package com.zexa.bridge

import java.security.SecureRandom
import java.util.UUID

/**
 * In-memory, one-use approval tickets for exact device-action requests.
 * This registry is deliberately not wired to execution yet: bridge actions
 * remain fail-closed until the foreground confirmation UI and timeout handoff
 * are integrated and tested end-to-end.
 */
data class PendingDeviceAction(
    val requestId: String,
    val action: String,
    val payloadJson: String,
    val createdAtEpochMs: Long,
    val expiresAtEpochMs: Long,
)

class ActionApprovalRegistry(
    private val ttlMs: Long = DEFAULT_TTL_MS,
    private val maxPending: Int = MAX_PENDING,
    private val idFactory: () -> String = { UUID.randomUUID().toString() },
) {
    private val pending = LinkedHashMap<String, PendingDeviceAction>()

    init {
        require(ttlMs in 1_000L..MAX_TTL_MS)
        require(maxPending in 1..MAX_PENDING)
    }

    @Synchronized
    fun create(action: String, payloadJson: String, nowMs: Long): PendingDeviceAction {
        require(action in ALLOWED_ACTIONS) { "Device action is not allowlisted." }
        require(payloadJson.isNotBlank() && payloadJson.length <= MAX_PAYLOAD_CHARS) {
            "Device action payload is empty or too large."
        }
        require(nowMs >= 0L)
        expire(nowMs)
        require(pending.size < maxPending) { "Too many pending device-action approvals." }
        val id = idFactory()
        require(id.isNotBlank() && id.length <= 64 && !pending.containsKey(id)) {
            "Could not create a unique approval request."
        }
        val request = PendingDeviceAction(id, action, payloadJson, nowMs, nowMs + ttlMs)
        pending[id] = request
        return request
    }

    @Synchronized
    fun list(nowMs: Long): List<PendingDeviceAction> {
        expire(nowMs)
        return pending.values.toList()
    }

    /** Consumes exactly one unexpired ticket. A second approval returns null. */
    @Synchronized
    fun approve(requestId: String, nowMs: Long): PendingDeviceAction? {
        expire(nowMs)
        if (requestId.isBlank()) return null
        return pending.remove(requestId)
    }

    @Synchronized
    fun deny(requestId: String): Boolean = pending.remove(requestId) != null

    @Synchronized
    fun clear() = pending.clear()

    private fun expire(nowMs: Long) {
        val iterator = pending.values.iterator()
        while (iterator.hasNext()) {
            if (iterator.next().expiresAtEpochMs <= nowMs) iterator.remove()
        }
    }

    companion object {
        const val DEFAULT_TTL_MS = 60_000L
        const val MAX_TTL_MS = 120_000L
        const val MAX_PENDING = 8
        const val MAX_PAYLOAD_CHARS = 16_000
        val ALLOWED_ACTIONS = setOf("tap", "swipe", "scroll", "back", "home", "input_text", "launch_app")
    }
}
