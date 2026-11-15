package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.atomic.AtomicInteger

class ChatGenerationGateTest {
    @Test
    fun onlyOneGenerationCanOwnTheNativeRuntime() {
        ChatGenerationGate.finish()

        assertTrue(ChatGenerationGate.tryStart())
        assertTrue(ChatGenerationGate.isRunning)
        assertFalse(ChatGenerationGate.tryStart())

        ChatGenerationGate.finish()
        assertFalse(ChatGenerationGate.isRunning)
        assertTrue(ChatGenerationGate.tryStart())

        ChatGenerationGate.finish()
    }
    @Test
    fun completionNotifiesRegisteredObserversAndSupportsRemoval() {
        ChatGenerationGate.finish()
        val notifications = AtomicInteger(0)
        val listener: () -> Unit = { notifications.incrementAndGet() }

        ChatGenerationGate.addCompletionListener(listener)
        assertTrue(ChatGenerationGate.tryStart())
        ChatGenerationGate.finish()
        assertEquals(1, notifications.get())

        ChatGenerationGate.addCompletionListener(listener)
        ChatGenerationGate.removeCompletionListener(listener)
        assertTrue(ChatGenerationGate.tryStart())
        ChatGenerationGate.finish()
        assertEquals(1, notifications.get())
    }

}
