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
    fun malformedStoredDataDoesNotCrash() {
        saved = "not-json"
        assertTrue(store.list().isEmpty())
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsUnknownAuditStatus() {
        store.append(ActionAuditEntry("req", "tap", "executed_without_approval", 1L))
    }
}
