package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class TaskActionGrantRegistryTest {
    @Test
    fun grantIsScopedToOneTaskDeviceAndActionSet() {
        val registry = TaskActionGrantRegistry(idFactory = { "grant-1" })
        val grant = registry.create(
            taskId = "task-1",
            deviceId = "phone-1",
            actions = setOf("scroll", "back"),
            nowElapsedMs = 10_000L,
            nowEpochMs = 100_000L,
            maxActions = 3,
        )

        assertEquals(3, grant.remainingActions)
        assertNull(registry.consume("grant-1", "task-2", "phone-1", "scroll", 10_001L))
        assertNull(registry.consume("grant-1", "task-1", "phone-2", "scroll", 10_002L))
        assertNull(registry.consume("grant-1", "task-1", "phone-1", "home", 10_003L))

        val consumed = registry.consume("grant-1", "task-1", "phone-1", "scroll", 10_004L)
        assertNotNullGrant(consumed)
        assertEquals(2, consumed!!.remainingActions)
    }

    @Test
    fun returnedActionScopeCannotBeMutated() {
        val registry = TaskActionGrantRegistry(idFactory = { "immutable" })
        val grant = registry.create("task-1", "phone-1", setOf("back"), 1L, 100_000L)
        try {
            (grant.allowedActions as MutableSet<String>).add("tap")
            throw AssertionError("Grant action scope was mutable.")
        } catch (_: UnsupportedOperationException) {
        }
        assertNull(registry.consume("immutable", "task-1", "phone-1", "tap", 2L))
    }

    @Test
    fun coordinateTapsAndTextEntryCannotBeGranted() {
        val registry = TaskActionGrantRegistry()
        assertRejected {
            registry.create("task-1", "phone-1", setOf("tap"), 1L, 100_000L)
        }
        assertRejected {
            registry.create("task-1", "phone-1", setOf("input_text"), 1L, 100_000L)
        }
        assertRejected {
            registry.create("task-1", "phone-1", setOf("open_url"), 1L, 100_000L)
        }
        assertRejected {
            registry.create("task-1", "phone-1", emptySet(), 1L, 100_000L)
        }
    }

    @Test
    fun grantExpiresAndCannotBeRevivedByAnOlderClockSample() {
        val registry = TaskActionGrantRegistry(
            maxTtlMs = 2_000L,
            idFactory = { "expires" },
        )
        registry.create(
            "task-1", "phone-1", setOf("scroll"),
            nowElapsedMs = 10_000L, nowEpochMs = 100_000L, ttlMs = 1_000L,
        )

        assertTrue(registry.list(10_999L).isNotEmpty())
        assertTrue(registry.list(11_000L).isEmpty())
        assertNull(registry.consume("expires", "task-1", "phone-1", "scroll", 10_001L))
    }

    @Test
    fun actionBudgetIsEnforcedAndGrantIsRemovedWhenExhausted() {
        val registry = TaskActionGrantRegistry(idFactory = { "budget" })
        registry.create(
            "task-1", "phone-1", setOf("scroll"),
            nowElapsedMs = 1L, nowEpochMs = 100_000L, maxActions = 2,
        )

        assertEquals(1, registry.consume("budget", "task-1", "phone-1", "scroll", 2L)!!.remainingActions)
        assertEquals(0, registry.consume("budget", "task-1", "phone-1", "scroll", 3L)!!.remainingActions)
        assertNull(registry.consume("budget", "task-1", "phone-1", "scroll", 4L))
        assertTrue(registry.list(4L).isEmpty())
    }

    @Test
    fun concurrentConsumersCannotExceedTheGrantActionBudget() {
        val registry = TaskActionGrantRegistry(idFactory = { "one-use-grant" })
        registry.create(
            "task-1", "phone-1", setOf("scroll"),
            nowElapsedMs = 1L, nowEpochMs = 100_000L, maxActions = 1,
        )
        val start = CountDownLatch(1)
        val finished = CountDownLatch(2)
        val outcomes = Collections.synchronizedList(mutableListOf<TaskActionGrant?>())
        val threads = (1..2).map { offset ->
            Thread {
                try {
                    start.await()
                    outcomes.add(
                        registry.consume(
                            "one-use-grant", "task-1", "phone-1", "scroll", 10L + offset,
                        )
                    )
                } finally {
                    finished.countDown()
                }
            }.apply { start() }
        }
        start.countDown()
        assertTrue("Concurrent grant consumers timed out.", finished.await(5, TimeUnit.SECONDS))
        threads.forEach { it.join(1_000L) }
        assertEquals(2, outcomes.size)
        assertEquals(1, outcomes.count { it != null })
        assertEquals(1, outcomes.count { it == null })
        assertTrue(registry.list(20L).isEmpty())
    }

    @Test
    fun revokeAndClearInvalidateActiveGrants() {
        val registry = TaskActionGrantRegistry(idFactory = { "revoke-1" })
        registry.create("task-1", "phone-1", setOf("back"), 1L, 100_000L)
        assertTrue(registry.revoke("revoke-1"))
        assertFalse(registry.revoke("revoke-1"))
        assertNull(registry.consume("revoke-1", "task-1", "phone-1", "back", 2L))

        registry.create("task-2", "phone-1", setOf("home"), 3L, 100_000L)
        registry.clear()
        assertTrue(registry.list(4L).isEmpty())
    }

    @Test
    fun duplicateGrantIdsAndExcessActiveGrantsAreRejected() {
        val duplicateRegistry = TaskActionGrantRegistry(idFactory = { "same-id" })
        duplicateRegistry.create("task-1", "phone-1", setOf("back"), 1L, 100_000L)
        assertRejected {
            duplicateRegistry.create("task-2", "phone-1", setOf("home"), 2L, 100_000L)
        }

        var nextId = 0
        val boundedRegistry = TaskActionGrantRegistry(
            maxGrants = 2,
            idFactory = { "grant-${++nextId}" },
        )
        boundedRegistry.create("task-1", "phone-1", setOf("back"), 1L, 100_000L)
        boundedRegistry.create("task-2", "phone-1", setOf("home"), 2L, 100_000L)
        assertRejected {
            boundedRegistry.create("task-3", "phone-1", setOf("scroll"), 3L, 100_000L)
        }
    }

    @Test
    fun rejectsInvalidBoundsAndIdentifiers() {
        val registry = TaskActionGrantRegistry()
        assertRejected { registry.create("../task", "phone-1", setOf("back"), 1L, 100_000L) }
        assertRejected { registry.create("task-1", "phone-1", setOf("back"), 1L, 100_000L, ttlMs = 999L) }
        assertRejected { registry.create("task-1", "phone-1", setOf("back"), 1L, 100_000L, maxActions = 101) }
    }

    private fun assertNotNullGrant(grant: TaskActionGrant?) {
        assertTrue(grant != null)
    }

    private fun assertRejected(block: () -> Unit) {
        try {
            block()
            throw AssertionError("Expected invalid task grant to be rejected.")
        } catch (_: IllegalArgumentException) {
        } catch (_: IllegalStateException) {
        }
    }
}
