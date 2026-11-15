package com.zexa.bridge

import android.content.Context
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Small process-local UI event hub. The durable work state itself is stored by
 * WorkManager; this only refreshes screens while the process is alive.
 */
object ModelLoadCoordinator {
    private val listeners = CopyOnWriteArrayList<(String, String?) -> Unit>()

    fun addListener(listener: (String, String?) -> Unit) { listeners.addIfAbsent(listener) }
    fun removeListener(listener: (String, String?) -> Unit) { listeners.remove(listener) }

    @Synchronized
    fun publish(context: Context, state: String, detail: String? = null) {
        context.getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE).edit()
            .putString("model_load_state", state)
            .putString("model_load_detail", detail)
            .apply()
        notifyListeners(state, detail)
    }

    /**
     * WorkManager may invoke onStopped after cancellation or a stop race.
     * Never let that callback overwrite a terminal loaded/failed result.
     */
    @Synchronized
    fun publishInterruptedIfActive(context: Context, detail: String): Boolean {
        val current = savedState(context).first
        if (!shouldPublishInterrupted(current)) return false
        publish(context, "interrupted", detail)
        return true
    }

    /**
     * A worker may finish native loading after WorkManager has stopped it.
     * Only an active load may transition to loaded; an interruption that
     * already won the race remains visible instead of being overwritten.
     */
    @Synchronized
    fun publishLoadedIfActive(context: Context, detail: String): Boolean {
        val current = savedState(context).first
        if (!shouldPublishLoaded(current)) return false
        publish(context, "loaded", detail)
        return true
    }

    internal fun shouldPublishLoaded(state: String): Boolean =
        state in ACTIVE_STATES

    private fun notifyListeners(state: String, detail: String?) {
        listeners.forEach { listener ->
            try { listener(state, detail) } catch (_: Exception) { /* UI observers are isolated. */ }
        }
    }

    fun savedState(context: Context): Pair<String, String?> {
        val prefs = context.getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE)
        return (prefs.getString("model_load_state", "idle") ?: "idle") to
            prefs.getString("model_load_detail", null)
    }

    internal fun shouldPublishInterrupted(state: String): Boolean =
        state in ACTIVE_STATES

    internal fun stateLabel(state: String, nativeLoaded: Boolean, detail: String?): String =
        when (state) {
            "queued" -> "Queued"
            "checking" -> "Checking model integrity"
            "loading" -> "Loading into native memory"
            "waiting" -> "Waiting for current chat"
            "loaded" -> if (nativeLoaded) "Loaded" else "Previously loaded; native runtime restarted"
            "failed" -> "Failed: " + (detail ?: "unknown error")
            "interrupted" -> "Interrupted: " + (detail ?: "tap retry")
            else -> if (nativeLoaded) "Loaded" else "Not loaded"
        }

    private val ACTIVE_STATES = setOf("queued", "waiting", "checking", "loading")
}
