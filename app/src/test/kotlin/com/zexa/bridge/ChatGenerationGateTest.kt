package com.zexa.bridge

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

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
}
