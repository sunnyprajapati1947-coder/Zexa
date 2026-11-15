package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ActionApprovalRegistryTest {
    @Test
    fun requestIsVisibleWithExactActionAndPayload() {
        val registry = ActionApprovalRegistry(idFactory = { "request-1" })
        val request = registry.create("tap", """{"x":120,"y":240}""", 10_000L)
        assertEquals("tap", request.action)
        assertEquals("""{"x":120,"y":240}""", request.payloadJson)
        assertEquals(request, registry.list(10_001L).single())
    }

    @Test
    fun approvalConsumesTicketExactlyOnce() {
        val registry = ActionApprovalRegistry(idFactory = { "one-use" })
        registry.create("back", "{}", 5_000L)
        assertNotNull(registry.approve("one-use", 5_001L))
        assertNull(registry.approve("one-use", 5_002L))
    }

    @Test
    fun expiredRequestCannotBeApproved() {
        val registry = ActionApprovalRegistry(ttlMs = 1_000L, idFactory = { "expires" })
        registry.create("home", "{}", 10_000L)
        assertTrue(registry.list(10_999L).isNotEmpty())
        assertTrue(registry.list(11_000L).isEmpty())
        assertNull(registry.approve("expires", 11_000L))
    }

    @Test
    fun deniedRequestCannotBeReused() {
        val registry = ActionApprovalRegistry(idFactory = { "denied" })
        registry.create("input_text", """{"text":"hello"}""", 1L)
        assertTrue(registry.deny("denied"))
        assertFalse(registry.deny("denied"))
        assertNull(registry.approve("denied", 2L))
    }

    @Test
    fun clearingRegistryInvalidatesAllPendingTickets() {
        val registry = ActionApprovalRegistry(idFactory = { "cleared" })
        registry.create("tap", """{"x":10,"y":20}""", 100L)
        registry.clear()
        assertTrue(registry.list(101L).isEmpty())
        assertNull(registry.approve("cleared", 102L))
    }

    @Test
    fun rejectsUnknownActionsAndOversizedPayloads() {
        val registry = ActionApprovalRegistry()
        assertRejected { registry.create("delete_everything", "{}", 1L) }
        assertRejected { registry.create("tap", "x".repeat(ActionApprovalRegistry.MAX_PAYLOAD_CHARS + 1), 1L) }
        assertRejected { registry.create("tap", " ", 1L) }
    }

    @Test
    fun rejectsTimestampOverflow() {
        val registry = ActionApprovalRegistry()
        assertRejected { registry.create("back", "{}", Long.MAX_VALUE) }
    }

    @Test
    fun pendingQueueIsBounded() {
        val registry = ActionApprovalRegistry(idFactory = { UUIDs.next() })
        repeat(ActionApprovalRegistry.MAX_PENDING) { index ->
            registry.create("back", "{}", index.toLong() + 1L)
        }
        assertRejected { registry.create("home", "{}", 20L) }
    }

    private fun assertRejected(block: () -> Unit) {
        try {
            block()
            throw AssertionError("Expected request to be rejected.")
        } catch (_: IllegalArgumentException) {
        } catch (_: IllegalStateException) {
        }
    }

    private object UUIDs {
        private var value = 0
        fun next(): String = "ticket-${++value}"
    }
}
