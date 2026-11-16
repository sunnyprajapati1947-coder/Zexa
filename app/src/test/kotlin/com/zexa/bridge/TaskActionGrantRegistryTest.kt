package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

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
    fun coordinateTapsAndTextEntryCannotBeGranted() {
        val registry = TaskActionGrantRegistry()
        assertRejected {
            registry.create("task-1", "phone-1", setOf("tap"), 1L, 100_000L)
        }
        assertRejected {
            registry.create("task-1", "phone-1", setOf("input_text"), 1L, 100_000L)
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
