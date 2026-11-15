package com.zexa.bridge

import java.util.concurrent.atomic.AtomicBoolean

/**
 * Process-wide guard for the single native llama.cpp context.
 * A new Activity must not start a second generation while an older Activity's
 * worker is still using the process-level JNI runtime.
 */
object ChatGenerationGate {
    private val running = AtomicBoolean(false)

    val isRunning: Boolean
        get() = running.get()

    fun tryStart(): Boolean = running.compareAndSet(false, true)

    fun finish() {
        running.set(false)
    }
}
