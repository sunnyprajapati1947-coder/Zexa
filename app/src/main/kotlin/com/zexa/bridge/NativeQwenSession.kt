package com.zexa.bridge

import java.io.File
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Process-scoped owner for the single llama.cpp model/context.
 *
 * The native runtime is process-wide, not Activity-wide. Every load, unload
 * and generation is serialized here so Activity recreation cannot cause a
 * second model load or race native context access.
 */
object NativeQwenSession {
    private var loadedModelPath: String? = null
    private val stateListeners = CopyOnWriteArrayList<() -> Unit>()

    val isLoaded: Boolean
        @Synchronized get() = loadedModelPath != null

    fun addStateListener(listener: () -> Unit) { stateListeners.addIfAbsent(listener) }

    fun removeStateListener(listener: () -> Unit) { stateListeners.remove(listener) }

    private fun notifyStateChanged() {
        stateListeners.forEach { listener ->
            try { listener() } catch (_: Exception) { /* UI observers cannot break runtime ownership. */ }
        }
    }

    @Synchronized
    fun load(model: File, contextSize: Int = 2048, threads: Int = 4) {
        val path = model.canonicalPath
        if (loadedModelPath == path) return
        unloadLocked()
        NativeQwenRuntime.nativeLoadModel(path, contextSize, threads)
        loadedModelPath = path
        notifyStateChanged()
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
        val imported = importer()
        notifyStateChanged()
        return imported
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
        notifyStateChanged()
    }
}
