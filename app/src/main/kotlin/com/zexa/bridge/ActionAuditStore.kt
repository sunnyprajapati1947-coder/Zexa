package com.zexa.bridge

import org.json.JSONArray
import org.json.JSONObject

/**
 * Bounded, payload-free audit trail for user-reviewed device actions.
 * Only request metadata and the final decision are persisted; action payloads
 * and screen contents are deliberately excluded.
 */
data class ActionAuditEntry(
    val requestId: String,
    val action: String,
    val status: String,
    val timestampEpochMs: Long,
)

class ActionAuditStore(
    private val read: () -> String?,
    private val write: (String) -> Unit,
    private val maxEntries: Int = MAX_ENTRIES,
) {
    init { require(maxEntries in 1..MAX_ENTRIES) }

    @Synchronized
    fun append(entry: ActionAuditEntry) {
        require(entry.requestId.isNotBlank() && entry.requestId.length <= 64)
        require(entry.action in ALLOWED_ACTIONS)
        require(entry.status in ALLOWED_STATUSES)
        require(entry.timestampEpochMs >= 0L)
        val entries = readEntries().toMutableList()
        entries.removeAll { it.requestId == entry.requestId }
        entries.add(entry)
        val bounded = entries.takeLast(maxEntries)
        writeEntries(bounded)
    }

    private fun writeEntries(entries: List<ActionAuditEntry>) {
        val json = JSONArray()
        entries.takeLast(maxEntries).forEach {
            json.put(JSONObject()
                .put("request_id", it.requestId)
                .put("action", it.action)
                .put("status", it.status)
                .put("timestamp_epoch_ms", it.timestampEpochMs))
        }
        write(json.toString())
    }

    @Synchronized
    fun markPendingAsInterrupted(nowMs: Long) {
        require(nowMs >= 0L)
        val entries = readEntries().toMutableList()
        var changed = false
        for (index in entries.indices) {
            if (entries[index].status in setOf("pending_approval", "executing")) {
                entries[index] = entries[index].copy(status = "interrupted", timestampEpochMs = nowMs)
                changed = true
            }
        }
        if (changed) writeEntries(entries)
    }

    @Synchronized
    fun list(): List<ActionAuditEntry> = readEntries().asReversed()

    private fun readEntries(): List<ActionAuditEntry> {
        val raw = read() ?: return emptyList()
        return try {
            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    val id = item.optString("request_id")
                    val action = item.optString("action")
                    val status = item.optString("status")
                    val timestamp = item.optLong("timestamp_epoch_ms", -1L)
                    if (id.isNotBlank() && id.length <= 64 &&
                        action in ALLOWED_ACTIONS &&
                        status in ALLOWED_STATUSES && timestamp >= 0L
                    ) add(ActionAuditEntry(id, action, status, timestamp))
                }
            }.takeLast(maxEntries)
        } catch (_: Exception) {
            emptyList()
        }
    }

    companion object {
        const val MAX_ENTRIES = 100
        val ALLOWED_ACTIONS = ActionApprovalRegistry.ALLOWED_ACTIONS + "task_grant"
        val ALLOWED_STATUSES = setOf("pending_approval", "executing", "dispatched", "completed", "failed", "execution_unknown", "denied", "interrupted", "expired", "created", "revoked")
    }
}
