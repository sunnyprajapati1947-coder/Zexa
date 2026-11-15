package com.zexa.bridge

import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Process-wide guard for the single native llama.cpp context.
 * Completion listeners let a recreated Activity refresh its UI after the
 * previous Activity's generation worker finishes.
 */
object ChatGenerationGate {
    private val running = AtomicBoolean(false)
    private val listeners = CopyOnWriteArrayList<() -> Unit>()

    val isRunning: Boolean
        get() = running.get()

    fun tryStart(): Boolean = running.compareAndSet(false, true)

    fun addCompletionListener(listener: () -> Unit) {
        listeners.addIfAbsent(listener)
    }

    fun removeCompletionListener(listener: () -> Unit) {
        listeners.remove(listener)
    }

    fun finish() {
        running.set(false)
        listeners.forEach { listener ->
            try {
                listener()
            } catch (_: Exception) {
                // A UI observer must not break native-runtime cleanup.
            }
        }
    }
}
