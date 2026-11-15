package com.zexa.bridge

import java.io.File

/**
 * Process-scoped owner for the single llama.cpp model/context.
 *
 * The native runtime is process-wide, not Activity-wide. Every load, unload
 * and generation is serialized here so Activity recreation cannot cause a
 * second model load or race native context access.
 */
object NativeQwenSession {
    private var loadedModelPath: String? = null

    val isLoaded: Boolean
        @Synchronized get() = loadedModelPath != null

    @Synchronized
    fun load(model: File, contextSize: Int = 2048, threads: Int = 4) {
        val path = model.canonicalPath
        if (loadedModelPath == path) return
        unloadLocked()
        NativeQwenRuntime.nativeLoadModel(path, contextSize, threads)
        loadedModelPath = path
    }

    @Synchronized
    fun unload() {
        unloadLocked()
    }

    /**
     * Prevents an import from replacing the GGUF while native code still has
     * the old file mapped. The importer runs only after native unload succeeds.
     */
    @Synchronized
    fun replaceModel(importer: () -> ImportedModel): ImportedModel {
        unloadLocked()
        return importer()
    }

    @Synchronized
    fun generate(
        systemPrompt: String,
        roles: Array<String>,
        contents: Array<String>,
        maxTokens: Int,
    ): String {
        check(loadedModelPath != null) { "Load a local Qwen model before generating." }
        return NativeQwenRuntime.nativeGenerate(systemPrompt, roles, contents, maxTokens)
    }

    private fun unloadLocked() {
        if (loadedModelPath == null) return
        NativeQwenRuntime.nativeUnloadModel()
        loadedModelPath = null
    }
}
