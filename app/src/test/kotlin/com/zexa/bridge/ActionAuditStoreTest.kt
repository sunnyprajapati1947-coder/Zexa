package com.zexa.bridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ActionAuditStoreTest {
    private var saved: String? = null
    private val store = ActionAuditStore({ saved }, { saved = it })

    @Test
    fun persistsOnlyMetadataAndCanBeReadAfterRecreation() {
        store.append(ActionAuditEntry("req-1", "tap", "pending_approval", 100L))
        val restored = ActionAuditStore({ saved }, { saved = it })
        assertEquals(
            listOf(ActionAuditEntry("req-1", "tap", "pending_approval", 100L)),
            restored.list(),
        )
        assertTrue(saved!!.contains("req-1"))
        assertTrue(!saved!!.contains("payload"))
    }

    @Test
    fun latestDecisionReplacesPendingRecord() {
        store.append(ActionAuditEntry("req-1", "back", "pending_approval", 100L))
        store.append(ActionAuditEntry("req-1", "back", "denied", 120L))
        assertEquals(listOf(ActionAuditEntry("req-1", "back", "denied", 120L)), store.list())
    }

    @Test
    fun historyIsBoundedAndNewestFirst() {
        val bounded = ActionAuditStore({ saved }, { saved = it }, maxEntries = 2)
        bounded.append(ActionAuditEntry("a", "back", "completed", 1L))
        bounded.append(ActionAuditEntry("b", "home", "failed", 2L))
        bounded.append(ActionAuditEntry("c", "tap", "denied", 3L))
        assertEquals(listOf("c", "b"), bounded.list().map { it.requestId })
    }

    @Test
    fun dispatchedGestureStatusIsAudited() {
        store.append(ActionAuditEntry("req-gesture", "swipe", "dispatched", 150L))
        assertEquals(
            listOf(ActionAuditEntry("req-gesture", "swipe", "dispatched", 150L)),
            store.list(),
        )
    }

    @Test
    fun taskGrantCreationAndRevocationAreAudited() {
        store.append(ActionAuditEntry("grant-created-123", "task_grant", "created", 100L))
        store.append(ActionAuditEntry("grant-revoked-123", "task_grant", "revoked", 200L))
        assertEquals(
            listOf(
                ActionAuditEntry("grant-revoked-123", "task_grant", "revoked", 200L),
                ActionAuditEntry("grant-created-123", "task_grant", "created", 100L),
            ),
            store.list(),
        )
    }

    @Test
    fun uncertainExecutionOutcomeIsAuditedWithoutClaimingFailure() {
        store.append(ActionAuditEntry("req-unknown", "tap", "execution_unknown", 175L))
        assertEquals(
            listOf(ActionAuditEntry("req-unknown", "tap", "execution_unknown", 175L)),
            store.list(),
        )
    }

    @Test
    fun malformedStoredDataDoesNotCrash() {
        saved = "not-json"
        assertTrue(store.list().isEmpty())
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsUnknownAuditStatus() {
        store.append(ActionAuditEntry("req", "tap", "executed_without_approval", 1L))
    }
    @Test
    fun pendingRequestsBecomeInterruptedAfterProcessRestart() {
        store.append(ActionAuditEntry("req-2", "launch_app", "pending_approval", 100L))
        val restored = ActionAuditStore({ saved }, { saved = it })
        restored.markPendingAsInterrupted(200L)
        assertEquals(
            listOf(ActionAuditEntry("req-2", "launch_app", "interrupted", 200L)),
            restored.list(),
        )
    }

    @Test
    fun terminalEntriesAreNotChangedDuringRecovery() {
        store.append(ActionAuditEntry("req-3", "home", "completed", 100L))
        store.markPendingAsInterrupted(200L)
        assertEquals("completed", store.list().single().status)
    }

}
