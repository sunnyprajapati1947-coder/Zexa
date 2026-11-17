package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class ActionApprovalRegistryTest {

    @Test
    fun requestIsVisibleWithExactActionAndPayload() {
        val registry = ActionApprovalRegistry(idFactory = { "request-1" })
        val request = registry.create("tap", """{"x":120,"y":240}""", 10_000L, 100_000L)

        assertEquals("tap", request.action)
        assertEquals("""{"x":120,"y":240}""", request.payloadJson)
        assertEquals(70_000L, request.expiresAtElapsedRealtimeMs)
        assertEquals(request, registry.list(10_001L).single())
    }

    @Test
    fun approvalConsumesTicketExactlyOnce() {
        val registry = ActionApprovalRegistry(idFactory = { "one-use" })
        registry.create("back", "{}", 5_000L, 100_000L)

        assertNotNull(registry.approve("one-use", 5_001L))
        assertNull(registry.approve("one-use", 5_002L))
    }

    @Test
    fun expiredRequestCannotBeApproved() {
        val registry = ActionApprovalRegistry(ttlMs = 1_000L, idFactory = { "expires" })
        registry.create("home", "{}", 10_000L, 100_000L)

        assertTrue(registry.list(10_999L).isNotEmpty())
        assertTrue(registry.list(11_000L).isEmpty())
        assertNull(registry.approve("expires", 11_000L))
        assertEquals("expires", registry.drainExpired().single().requestId)
        assertTrue(registry.drainExpired().isEmpty())
    }

    @Test
    fun atomicExpiryDrainCollectsBoundaryExpiryExactlyOnce() {
        val registry = ActionApprovalRegistry(ttlMs = 1_000L, idFactory = { "atomic-expiry" })
        registry.create("back", "{}", 2_000L, 100_000L)

        assertEquals("atomic-expiry", registry.expireAndDrain(3_000L).single().requestId)
        assertTrue(registry.expireAndDrain(3_001L).isEmpty())
        assertNull(registry.approve("atomic-expiry", 3_002L))
    }

    @Test
    fun expiredTicketsAreRetainedForAuditWhenListTriggersExpiry() {
        val registry = ActionApprovalRegistry(ttlMs = 1_000L, idFactory = { "audit-expiry" })
        registry.create("tap", "{}", 5_000L, 100_000L)

        assertTrue(registry.list(6_000L).isEmpty())
        assertEquals("audit-expiry", registry.drainExpired().single().requestId)
        assertTrue(registry.drainExpired().isEmpty())
    }

    @Test
    fun expiredRequestIdCannotBeReusedBeforeItsAuditRecordIsDrained() {
        var candidateId = "reused"
        val registry = ActionApprovalRegistry(ttlMs = 1_000L, idFactory = { candidateId })
        registry.create("back", "{}", 1_000L, 100_000L)

        assertTrue(registry.list(2_000L).isEmpty())
        assertRejected { registry.create("home", "{}", 2_001L, 101_000L) }
        assertEquals("reused", registry.drainExpired().single().requestId)

        candidateId = "replacement"
        val replacement = registry.create("home", "{}", 2_002L, 101_001L)
        assertEquals("replacement", replacement.requestId)
    }

    @Test
    fun deniedRequestCannotBeReused() {
        val registry = ActionApprovalRegistry(idFactory = { "denied" })
        registry.create("input_text", """{"text":"hello"}""", 1L, 100_000L)

        assertNotNull(registry.deny("denied", 2L))
        assertNull(registry.deny("denied", 3L))
        assertNull(registry.approve("denied", 4L))
    }

    @Test
    fun concurrentApproveAndDenyCanConsumeTicketOnlyOnce() {
        val registry = ActionApprovalRegistry(idFactory = { "race-ticket" })
        registry.create("back", "{}", 1L, 100_000L)

        val start = CountDownLatch(1)
        val finished = CountDownLatch(2)
        val outcomes = Collections.synchronizedList(
            mutableListOf<PendingDeviceAction?>()
        )
        val errors = Collections.synchronizedList(
            mutableListOf<Throwable>()
        )

        val approveThread = Thread {
            try {
                start.await()
                outcomes.add(registry.approve("race-ticket", 10L))
            } catch (error: Throwable) {
                errors.add(error)
            } finally {
                finished.countDown()
            }
        }

        val denyThread = Thread {
            try {
                start.await()
                outcomes.add(registry.deny("race-ticket", 10L))
            } catch (error: Throwable) {
                errors.add(error)
            } finally {
                finished.countDown()
            }
        }

        approveThread.start()
        denyThread.start()
        start.countDown()

        assertTrue("Concurrent operations timed out.", finished.await(5, TimeUnit.SECONDS))
        assertTrue("Concurrent operation failed: $errors", errors.isEmpty())
        assertEquals(2, outcomes.size)
        assertEquals(1, outcomes.count { it != null })
        assertEquals(1, outcomes.count { it == null })
    }

    @Test
    fun clearingRegistryInvalidatesAllPendingTickets() {
        val registry = ActionApprovalRegistry(idFactory = { "cleared" })
        registry.create("tap", """{"x":10,"y":20}""", 100L, 100_000L)

        registry.clear()

        assertTrue(registry.list(101L).isEmpty())
        assertNull(registry.approve("cleared", 102L))
    }

    @Test
    fun rejectsUnknownActionsAndOversizedPayloads() {
        val registry = ActionApprovalRegistry()

        assertRejected { registry.create("delete_everything", "{}", 1L, 100_000L) }
        assertRejected {
            registry.create(
                "tap",
                "x".repeat(ActionApprovalRegistry.MAX_PAYLOAD_CHARS + 1),
                1L,
                100_000L
            )
        }
        assertRejected { registry.create("tap", " ", 1L, 100_000L) }
    }

    @Test
    fun rejectsElapsedAndEpochTimestampOverflow() {
        val elapsedRegistry = ActionApprovalRegistry()
        val epochRegistry = ActionApprovalRegistry()

        assertRejected {
            elapsedRegistry.create("back", "{}", Long.MAX_VALUE, 100_000L)
        }
        assertRejected {
            epochRegistry.create("back", "{}", 1L, Long.MAX_VALUE)
        }
    }

    @Test
    fun pendingQueueIsBounded() {
        val registry = ActionApprovalRegistry(idFactory = { UUIDs.next() })

        repeat(ActionApprovalRegistry.MAX_PENDING) { index ->
            registry.create("back", "{}", index.toLong() + 1L, 100_000L)
        }

        assertRejected { registry.create("home", "{}", 20L, 100_000L) }
    }

    @Test
    fun staleClockSampleCannotReviveExpiredTicket() {
        val registry = ActionApprovalRegistry(
            ttlMs = 1_000L,
            idFactory = { "clock-test" }
        )
        registry.create("back", "{}", 100L, 100_000L)

        assertTrue(registry.list(1_100L).isEmpty())
        assertNull(registry.approve("clock-test", 101L))
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
