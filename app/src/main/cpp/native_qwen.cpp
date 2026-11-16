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
uint32_t loaded_context_size = 0;

void throw_java(JNIEnv * env, const char * message) {
    jclass error_class = env->FindClass("java/lang/IllegalStateException");
    if (error_class != nullptr) env->ThrowNew(error_class, message);
}

void append_utf8(std::string & output, uint32_t codepoint) {
    if (codepoint <= 0x7F) {
        output.push_back(static_cast<char>(codepoint));
    } else if (codepoint <= 0x7FF) {
        output.push_back(static_cast<char>(0xC0 | (codepoint >> 6)));
        output.push_back(static_cast<char>(0x80 | (codepoint & 0x3F)));
    } else if (codepoint <= 0xFFFF) {
        output.push_back(static_cast<char>(0xE0 | (codepoint >> 12)));
        output.push_back(static_cast<char>(0x80 | ((codepoint >> 6) & 0x3F)));
        output.push_back(static_cast<char>(0x80 | (codepoint & 0x3F)));
    } else {
        output.push_back(static_cast<char>(0xF0 | (codepoint >> 18)));
        output.push_back(static_cast<char>(0x80 | ((codepoint >> 12) & 0x3F)));
        output.push_back(static_cast<char>(0x80 | ((codepoint >> 6) & 0x3F)));
        output.push_back(static_cast<char>(0x80 | (codepoint & 0x3F)));
    }
}

std::string from_java(JNIEnv * env, jstring value) {
    if (value == nullptr) return {};
    const jsize length = env->GetStringLength(value);
    const jchar * chars = env->GetStringChars(value, nullptr);
    if (chars == nullptr) return {};
    std::string result;
    result.reserve(static_cast<size_t>(length) * 3);
    for (jsize i = 0; i < length; ++i) {
        uint32_t codepoint = chars[i];
        if (codepoint >= 0xD800 && codepoint <= 0xDBFF &&
            i + 1 < length && chars[i + 1] >= 0xDC00 && chars[i + 1] <= 0xDFFF) {
            codepoint = 0x10000 + ((codepoint - 0xD800) << 10) +
                        (static_cast<uint32_t>(chars[++i]) - 0xDC00);
        } else if (codepoint >= 0xD800 && codepoint <= 0xDFFF) {
            codepoint = 0xFFFD;
        }
        append_utf8(result, codepoint);
    }
    env->ReleaseStringChars(value, chars);
    return result;
}

jstring to_java(JNIEnv * env, const std::string & value) {
    std::vector<jchar> output;
    output.reserve(value.size());
    for (size_t i = 0; i < value.size();) {
        const uint8_t first = static_cast<uint8_t>(value[i++]);
        uint32_t codepoint = 0xFFFD;
        size_t continuation = 0;
        if (first <= 0x7F) {
            codepoint = first;
        } else if ((first & 0xE0) == 0xC0) {
            codepoint = first & 0x1F; continuation = 1;
        } else if ((first & 0xF0) == 0xE0) {
            codepoint = first & 0x0F; continuation = 2;
        } else if ((first & 0xF8) == 0xF0) {
            codepoint = first & 0x07; continuation = 3;
        }
        bool valid = i + continuation <= value.size();
        for (size_t j = 0; valid && j < continuation; ++j) {
            const uint8_t next = static_cast<uint8_t>(value[i++]);
            if ((next & 0xC0) != 0x80) {
                valid = false;
                break;
            }
            codepoint = (codepoint << 6) | (next & 0x3F);
        }
        if (!valid || codepoint > 0x10FFFF ||
            (codepoint >= 0xD800 && codepoint <= 0xDFFF)) {
            codepoint = 0xFFFD;
        }
        if (codepoint <= 0xFFFF) {
            output.push_back(static_cast<jchar>(codepoint));
        } else {
            codepoint -= 0x10000;
            output.push_back(static_cast<jchar>(0xD800 + (codepoint >> 10)));
            output.push_back(static_cast<jchar>(0xDC00 + (codepoint & 0x3FF)));
        }
    }
    return env->NewString(output.data(), static_cast<jsize>(output.size()));
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
    loaded_context_size = static_cast<uint32_t>(context_size);
    return;
}

extern "C" JNIEXPORT void JNICALL
Java_com_zexa_bridge_NativeQwenRuntime_nativeUnloadModel(JNIEnv *, jobject) {
    std::lock_guard<std::mutex> lock(runtime_mutex);
    release_runtime();
    loaded_context_size = 0;
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_zexa_bridge_NativeQwenRuntime_nativeGenerate(
        JNIEnv * env, jobject, jstring system_prompt, jobjectArray history_roles,
        jobjectArray history_contents, jint max_tokens) {
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
    const jsize history_count = history_roles == nullptr ? 0 : env->GetArrayLength(history_roles);
    if (history_contents == nullptr || history_count < 1 || history_count > 15 || (history_count % 2) == 0 ||
        env->GetArrayLength(history_contents) != history_count) {
        throw_java(env, "Chat history must contain between 1 and 16 matching messages.");
        return nullptr;
    }

    std::vector<std::string> roles;
    std::vector<std::string> contents;
    roles.reserve(static_cast<size_t>(history_count));
    contents.reserve(static_cast<size_t>(history_count));
    for (jsize index = 0; index < history_count; ++index) {
        auto role_value = static_cast<jstring>(env->GetObjectArrayElement(history_roles, index));
        auto content_value = static_cast<jstring>(env->GetObjectArrayElement(history_contents, index));
        const std::string role = from_java(env, role_value);
        const std::string content = from_java(env, content_value);
        if (role_value != nullptr) env->DeleteLocalRef(role_value);
        if (content_value != nullptr) env->DeleteLocalRef(content_value);
        const bool expected_user = (index % 2) == 0;
        if ((expected_user && role != "user") || (!expected_user && role != "assistant") ||
            content.empty() || content.size() > 16 * 1024) {
            throw_java(env, "Chat history roles or message sizes are invalid.");
            return nullptr;
        }
        roles.push_back(role);
        contents.push_back(content);
    }

    const char * chat_template = llama_model_chat_template(model, nullptr);
    if (chat_template == nullptr) {
        throw_java(env, "This GGUF model does not provide a chat template.");
        return nullptr;
    }

    const llama_vocab * vocab = llama_model_get_vocab(model);
    std::vector<char> prompt;
    std::vector<llama_token> tokens;
    int32_t formatted = 0;
    while (true) {
        std::vector<llama_chat_message> messages;
        messages.reserve(roles.size() + (system_text.empty() ? 0 : 1));
        if (!system_text.empty()) messages.push_back({"system", system_text.c_str()});
        for (size_t index = 0; index < roles.size(); ++index) {
            messages.push_back({roles[index].c_str(), contents[index].c_str()});
        }

        const int32_t prompt_length = llama_chat_apply_template(
            chat_template, messages.data(), messages.size(), true, nullptr, 0);
        if (prompt_length <= 0 || prompt_length > 256 * 1024) {
            throw_java(env, "Could not format the prompt using the model chat template.");
            return nullptr;
        }
        prompt.assign(static_cast<size_t>(prompt_length) + 1, '\0');
        formatted = llama_chat_apply_template(
            chat_template, messages.data(), messages.size(), true,
            prompt.data(), static_cast<int32_t>(prompt.size()));
        if (formatted < 0 || formatted > prompt_length) {
            throw_java(env, "Model chat template formatting failed.");
            return nullptr;
        }

        int32_t token_count = llama_tokenize(
            vocab, prompt.data(), formatted, nullptr, 0, true, true);
        if (token_count == INT32_MIN) {
            throw_java(env, "Could not determine prompt token count.");
            return nullptr;
        }
        if (token_count < 0) token_count = -token_count;
        if (token_count <= 0 || token_count > 4096) {
            throw_java(env, "Prompt tokenization failed.");
            return nullptr;
        }
        if (static_cast<uint32_t>(token_count) + static_cast<uint32_t>(max_tokens) <= loaded_context_size) {
            tokens.resize(static_cast<size_t>(token_count));
            const int32_t actual_tokens = llama_tokenize(
                vocab, prompt.data(), formatted, tokens.data(), token_count, true, true);
            if (actual_tokens < 0 || actual_tokens > token_count) {
                throw_java(env, "Prompt tokenization failed.");
                return nullptr;
            }
            tokens.resize(static_cast<size_t>(actual_tokens));
            break;
        }
        if (roles.size() <= 1) {
            throw_java(env, "The latest message exceeds the model context size.");
            return nullptr;
        }
        roles.erase(roles.begin(), roles.begin() + 2);
        contents.erase(contents.begin(), contents.begin() + 2);
    }

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
    const auto add_sampler = [sampler](llama_sampler * component) {
        if (component == nullptr) return false;
        llama_sampler_chain_add(sampler, component);
        return true;
    };
    if (!add_sampler(llama_sampler_init_top_k(40)) ||
        !add_sampler(llama_sampler_init_top_p(0.9f, 1)) ||
        !add_sampler(llama_sampler_init_temp(0.7f)) ||
        !add_sampler(llama_sampler_init_dist(LLAMA_DEFAULT_SEED))) {
        llama_sampler_free(sampler);
        throw_java(env, "Could not allocate all text sampling components.");
        return nullptr;
    }

    std::string answer;
    bool generation_failed = false;
    for (int32_t index = 0; index < max_tokens; ++index) {
        const llama_token token = llama_sampler_sample(sampler, context, -1);
        if (llama_vocab_is_eog(vocab, token)) break;
        llama_sampler_accept(sampler, token);

        char piece[256];
        int32_t piece_size = llama_token_to_piece(vocab, token, piece, sizeof(piece), 0, true);
        if (piece_size < 0) {
            const size_t required_size = static_cast<size_t>(-piece_size);
            if (required_size > static_cast<size_t>(INT32_MAX)) {
                generation_failed = true;
                break;
            }
            std::vector<char> expanded(required_size);
            piece_size = llama_token_to_piece(vocab, token, expanded.data(),
                                              static_cast<int32_t>(expanded.size()), 0, true);
            if (piece_size <= 0 || static_cast<size_t>(piece_size) > expanded.size()) {
                generation_failed = true;
                break;
            }
            answer.append(expanded.data(), static_cast<size_t>(piece_size));
        } else if (piece_size > 0 && piece_size <= static_cast<int32_t>(sizeof(piece))) {
            answer.append(piece, static_cast<size_t>(piece_size));
        } else {
            generation_failed = true;
            break;
        }

        llama_token next = token;
        llama_batch next_batch = llama_batch_get_one(&next, 1);
        if (llama_decode(context, next_batch) != 0) {
            generation_failed = true;
            break;
        }
    }
    llama_sampler_free(sampler);
    if (generation_failed) {
        throw_java(env, "Qwen generation failed while decoding a token. Please retry.");
        return nullptr;
    }
    return to_java(env, answer);
}
