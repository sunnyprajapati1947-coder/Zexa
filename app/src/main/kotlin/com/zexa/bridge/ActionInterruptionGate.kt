package com.zexa.bridge

/**
 * Invalidates service actions that were queued but have not started yet.
 * The generation is read on the Android service looper immediately before dispatch.
 */
class ActionInterruptionGate {
    @Volatile private var generation: Long = 0L

    fun current(): Long = generation

    @Synchronized
    fun invalidate(): Long {
        check(generation < Long.MAX_VALUE) { "Action interruption generation exhausted." }
        generation += 1L
        return generation
    }

    fun requireCurrent(expectedGeneration: Long) {
        check(generation == expectedGeneration) {
            "Android accessibility service was interrupted before action dispatch."
        }
    }
}
