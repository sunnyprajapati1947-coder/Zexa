package com.zexa.bridge

/**
 * JNI facade for the pinned llama.cpp CPU runtime.
 * Calls must run off the Android main thread; one model/context is held per app process.
 */
object NativeQwenRuntime {
    init {
        System.loadLibrary("zexa_llama")
    }

    @JvmStatic
    external fun nativeLoadModel(modelPath: String, contextSize: Int, threads: Int)

    @JvmStatic
    external fun nativeUnloadModel()

    @JvmStatic
    external fun nativeGenerate(systemPrompt: String, roles: Array<String>, contents: Array<String>, maxTokens: Int): String
}
