#include <jni.h>
#include <llama.h>

#include <algorithm>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

namespace {
std::mutex runtime_mutex;
llama_model * model = nullptr;
llama_context * context = nullptr;
bool backend_initialized = false;

void throw_java(JNIEnv * env, const char * message) {
    jclass error_class = env->FindClass("java/lang/IllegalStateException");
    if (error_class != nullptr) env->ThrowNew(error_class, message);
}

std::string from_java(JNIEnv * env, jstring value) {
    if (value == nullptr) return {};
    const char * chars = env->GetStringUTFChars(value, nullptr);
    if (chars == nullptr) return {};
    std::string result(chars);
    env->ReleaseStringUTFChars(value, chars);
    return result;
}

jstring to_java(JNIEnv * env, const std::string & value) {
    return env->NewStringUTF(value.c_str());
}

void release_runtime() {
    if (context != nullptr) {
        llama_free(context);
        context = nullptr;
    }
    if (model != nullptr) {
        llama_model_free(model);
        model = nullptr;
    }
}
}

extern "C" JNIEXPORT void JNICALL
Java_com_zexa_bridge_NativeQwenRuntime_nativeLoadModel(
        JNIEnv * env, jobject, jstring model_path, jint context_size, jint threads) {
    std::lock_guard<std::mutex> lock(runtime_mutex);
    const std::string path = from_java(env, model_path);
    if (path.empty()) {
        throw_java(env, "Model path is empty.");
        return;
    }
    if (context_size < 512 || context_size > 4096 || threads < 1 || threads > 8) {
        throw_java(env, "Unsupported context or thread configuration.");
        return;
    }

    if (!backend_initialized) {
        llama_backend_init();
        backend_initialized = true;
    }

    llama_model_params model_params = llama_model_default_params();
    model_params.n_gpu_layers = 0;
    llama_model * next_model = llama_model_load_from_file(path.c_str(), model_params);
    if (next_model == nullptr) {
        throw_java(env, "llama.cpp could not load this GGUF model.");
        return;
    }

    llama_context_params context_params = llama_context_default_params();
    context_params.n_ctx = static_cast<uint32_t>(context_size);
    context_params.n_batch = std::min<uint32_t>(context_params.n_batch, 512);
    context_params.n_ubatch = std::min<uint32_t>(context_params.n_ubatch, 512);
    context_params.n_threads = threads;
    context_params.n_threads_batch = threads;
    context_params.no_perf = true;

    llama_context * next_context = llama_init_from_model(next_model, context_params);
    if (next_context == nullptr) {
        llama_model_free(next_model);
        throw_java(env, "llama.cpp could not allocate the inference context. Try a smaller context or model.");
        return;
    }

    release_runtime();
    model = next_model;
    context = next_context;
    return;
}

extern "C" JNIEXPORT void JNICALL
Java_com_zexa_bridge_NativeQwenRuntime_nativeUnloadModel(JNIEnv *, jobject) {
    std::lock_guard<std::mutex> lock(runtime_mutex);
    release_runtime();
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_zexa_bridge_NativeQwenRuntime_nativeGenerate(
        JNIEnv * env, jobject, jstring system_prompt, jstring user_prompt, jint max_tokens) {
    std::lock_guard<std::mutex> lock(runtime_mutex);
    if (model == nullptr || context == nullptr) {
        throw_java(env, "Load a local GGUF model before starting a conversation.");
        return nullptr;
    }
    if (max_tokens < 1 || max_tokens > 512) {
        throw_java(env, "Output token limit must be between 1 and 512.");
        return nullptr;
    }

    const std::string system_text = from_java(env, system_prompt);
    const std::string user_text = from_java(env, user_prompt);
    if (user_text.empty()) {
        throw_java(env, "The user message is empty.");
        return nullptr;
    }
    const char * chat_template = llama_model_chat_template(model, nullptr);
    if (chat_template == nullptr) {
        throw_java(env, "This GGUF model does not provide a chat template.");
        return nullptr;
    }

    std::vector<llama_chat_message> messages;
    if (!system_text.empty()) {
        messages.push_back({"system", system_text.c_str()});
    }
    messages.push_back({"user", user_text.c_str()});
    int32_t prompt_length = llama_chat_apply_template(
        chat_template, messages.data(), messages.size(), true, nullptr, 0);
    if (prompt_length <= 0 || prompt_length > 256 * 1024) {
        throw_java(env, "Could not format the prompt using the model chat template.");
        return nullptr;
    }
    std::vector<char> prompt(static_cast<size_t>(prompt_length) + 1);
    const int32_t formatted = llama_chat_apply_template(
        chat_template, messages.data(), messages.size(), true,
        prompt.data(), static_cast<int32_t>(prompt.size()));
    if (formatted < 0 || formatted > prompt_length) {
        throw_java(env, "Model chat template formatting failed.");
        return nullptr;
    }

    const llama_vocab * vocab = llama_model_get_vocab(model);
    int32_t token_count = llama_tokenize(
        vocab, prompt.data(), formatted, nullptr, 0, true, true);
    if (token_count == INT32_MIN || token_count >= 0) {
        throw_java(env, "Could not determine prompt token count.");
        return nullptr;
    }
    token_count = -token_count;
    if (token_count <= 0 || token_count > 4096) {
        throw_java(env, "Prompt exceeds the supported context size.");
        return nullptr;
    }
    std::vector<llama_token> tokens(static_cast<size_t>(token_count));
    const int32_t actual_tokens = llama_tokenize(
        vocab, prompt.data(), formatted, tokens.data(), token_count, true, true);
    if (actual_tokens < 0 || actual_tokens > token_count) {
        throw_java(env, "Prompt tokenization failed.");
        return nullptr;
    }
    tokens.resize(static_cast<size_t>(actual_tokens));

    llama_memory_clear(llama_get_memory(context), true);
    const int32_t batch_size = 512;
    for (size_t offset = 0; offset < tokens.size(); offset += batch_size) {
        const int32_t count = static_cast<int32_t>(
            std::min<size_t>(batch_size, tokens.size() - offset));
        llama_batch batch = llama_batch_get_one(tokens.data() + offset, count);
        if (llama_decode(context, batch) != 0) {
            throw_java(env, "The model could not evaluate the prompt.");
            return nullptr;
        }
    }

    llama_sampler * sampler = llama_sampler_chain_init(llama_sampler_chain_default_params());
    if (sampler == nullptr) {
        throw_java(env, "Could not initialize the text sampler.");
        return nullptr;
    }
    llama_sampler_chain_add(sampler, llama_sampler_init_top_k(40));
    llama_sampler_chain_add(sampler, llama_sampler_init_top_p(0.9f, 1));
    llama_sampler_chain_add(sampler, llama_sampler_init_temp(0.7f));
    llama_sampler_chain_add(sampler, llama_sampler_init_dist(LLAMA_DEFAULT_SEED));

    std::string answer;
    for (int32_t index = 0; index < max_tokens; ++index) {
        const llama_token token = llama_sampler_sample(sampler, context, -1);
        if (llama_vocab_is_eog(vocab, token)) break;
        llama_sampler_accept(sampler, token);

        char piece[256];
        int32_t piece_size = llama_token_to_piece(vocab, token, piece, sizeof(piece), 0, true);
        if (piece_size < 0) {
            std::vector<char> expanded(static_cast<size_t>(-piece_size));
            piece_size = llama_token_to_piece(vocab, token, expanded.data(),
                                              static_cast<int32_t>(expanded.size()), 0, true);
            if (piece_size > 0) answer.append(expanded.data(), static_cast<size_t>(piece_size));
        } else if (piece_size > 0) {
            answer.append(piece, static_cast<size_t>(piece_size));
        }

        llama_token next = token;
        llama_batch next_batch = llama_batch_get_one(&next, 1);
        if (llama_decode(context, next_batch) != 0) break;
    }
    llama_sampler_free(sampler);
    return to_java(env, answer);
}
