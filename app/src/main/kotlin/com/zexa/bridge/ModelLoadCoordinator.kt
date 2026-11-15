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

    fun publish(context: Context, state: String, detail: String? = null) {
        context.getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE).edit()
            .putString("model_load_state", state)
            .putString("model_load_detail", detail)
            .apply()
        listeners.forEach { listener ->
            try { listener(state, detail) } catch (_: Exception) { /* UI observers are isolated. */ }
        }
    }

    fun savedState(context: Context): Pair<String, String?> {
        val prefs = context.getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE)
        return (prefs.getString("model_load_state", "idle") ?: "idle") to
            prefs.getString("model_load_detail", null)
    }
}
