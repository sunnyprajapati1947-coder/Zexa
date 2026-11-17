package com.zexa.bridge

/**
 * Invalidates service actions that were queued but have not started yet.
 * The generation is read on the Android service looper immediately before dispatch.
 */
internal class ActionInterruptedException : IllegalStateException("Android accessibility service was interrupted before action dispatch.")

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
        if (generation != expectedGeneration) throw ActionInterruptedException()
    }
}
