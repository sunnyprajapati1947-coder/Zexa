package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class ActionInterruptionGateTest {
    @Test
    fun currentGenerationRemainsValidUntilInterruption() {
        val gate = ActionInterruptionGate()
        val queuedGeneration = gate.current()

        gate.requireCurrent(queuedGeneration)
        assertEquals(queuedGeneration, gate.current())
    }

    @Test
    fun interruptionInvalidatesPreviouslyQueuedAction() {
        val gate = ActionInterruptionGate()
        val queuedGeneration = gate.current()

        gate.invalidate()

        try {
            gate.requireCurrent(queuedGeneration)
            fail("Expected stale queued action to be rejected.")
        } catch (expected: IllegalStateException) {
            assertTrue(expected is ActionInterruptedException)
            assertEquals(
                "Android accessibility service was interrupted before action dispatch.",
                expected.message
            )
        }
    }

    @Test
    fun actionQueuedAfterInterruptionUsesNewGeneration() {
        val gate = ActionInterruptionGate()
        gate.invalidate()
        val newGeneration = gate.current()

        gate.requireCurrent(newGeneration)
    }
}
