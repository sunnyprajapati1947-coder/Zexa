package com.zexa.bridge

import java.util.UUID

/**
 * In-memory, one-use approval tickets for exact device-action requests.
 * Expiry uses monotonic elapsed time; epoch timestamps remain for display/audit.
 */
data class PendingDeviceAction(
    val requestId: String,
    val action: String,
    val payloadJson: String,
    val createdAtEpochMs: Long,
    val expiresAtEpochMs: Long,
    val expiresAtElapsedRealtimeMs: Long,
)

class ActionApprovalRegistry(
    private val ttlMs: Long = DEFAULT_TTL_MS,
    private val maxPending: Int = MAX_PENDING,
    private val idFactory: () -> String = { UUID.randomUUID().toString() },
) {
    private data class Entry(
        val ticket: PendingDeviceAction,
        val deadlineElapsedMs: Long,
    )

    private val pending = LinkedHashMap<String, Entry>()
    private val expired = LinkedHashMap<String, PendingDeviceAction>()
    private var lastObservedElapsedMs = 0L

    init {
        require(ttlMs in 1_000L..MAX_TTL_MS)
        require(maxPending in 1..MAX_PENDING)
    }

    @Synchronized
    fun create(
        action: String,
        payloadJson: String,
        nowElapsedMs: Long,
        nowEpochMs: Long,
    ): PendingDeviceAction {
        require(action in ALLOWED_ACTIONS) { "Device action is not allowlisted." }
        require(payloadJson.isNotBlank() && payloadJson.length <= MAX_PAYLOAD_CHARS) {
            "Device action payload is empty or too large."
        }
        require(nowElapsedMs >= 0L && nowElapsedMs <= Long.MAX_VALUE - ttlMs) {
            "Invalid monotonic approval timestamp."
        }
        require(nowEpochMs >= 0L && nowEpochMs <= Long.MAX_VALUE - ttlMs) {
            "Invalid approval timestamp."
        }
        val effectiveNowMs = observeTime(nowElapsedMs)
        expire(effectiveNowMs)
        require(pending.size < maxPending) { "Too many pending device-action approvals." }

        val id = idFactory()
        require(id.isNotBlank() && id.length <= 64 && !pending.containsKey(id) && !expired.containsKey(id)) {
            "Could not create a unique approval request."
        }

        val deadline = effectiveNowMs + ttlMs
        val ticket = PendingDeviceAction(
            id, action, payloadJson, nowEpochMs, nowEpochMs + ttlMs, deadline,
        )
        pending[id] = Entry(ticket, deadline)
        return ticket
    }

    @Synchronized
    fun list(nowElapsedMs: Long): List<PendingDeviceAction> {
        val effectiveNowMs = observeTime(nowElapsedMs)
        expire(effectiveNowMs)
        return pending.values.map { it.ticket }
    }

    /** Consumes exactly one unexpired ticket. A second approval returns null. */
    @Synchronized
    fun approve(requestId: String, nowElapsedMs: Long): PendingDeviceAction? {
        val effectiveNowMs = observeTime(nowElapsedMs)
        expire(effectiveNowMs)
        if (requestId.isBlank()) return null
        return pending.remove(requestId)?.ticket
    }

    /** Atomically expires and removes a denied ticket, returning its audit details. */
    @Synchronized
    fun deny(requestId: String, nowElapsedMs: Long): PendingDeviceAction? {
        val effectiveNowMs = observeTime(nowElapsedMs)
        expire(effectiveNowMs)
        if (requestId.isBlank()) return null
        return pending.remove(requestId)?.ticket
    }

    /** Atomically expires due tickets and returns each newly expired ticket once. */
    @Synchronized
    fun expireAndDrain(nowElapsedMs: Long): List<PendingDeviceAction> {
        val effectiveNowMs = observeTime(nowElapsedMs)
        expire(effectiveNowMs)
        return expired.values.toList().also { expired.clear() }
    }

    /** Returns each expired ticket once, including tickets expired by list/create/approve/deny. */
    @Synchronized
    fun drainExpired(): List<PendingDeviceAction> = expired.values.toList().also { expired.clear() }

    @Synchronized
    fun clear() {
        pending.clear()
        expired.clear()
    }

    private fun observeTime(nowElapsedMs: Long): Long {
        require(nowElapsedMs >= 0L) {
            "Invalid monotonic approval timestamp."
        }
        if (nowElapsedMs > lastObservedElapsedMs) {
            lastObservedElapsedMs = nowElapsedMs
        }
        return lastObservedElapsedMs
    }

    private fun expire(nowElapsedMs: Long) {
        val iterator = pending.values.iterator()
        while (iterator.hasNext()) {
            val entry = iterator.next()
            if (entry.deadlineElapsedMs <= nowElapsedMs) {
                expired[entry.ticket.requestId] = entry.ticket
                iterator.remove()
            }
        }
    }

    companion object {
        const val DEFAULT_TTL_MS = 60_000L
        const val MAX_TTL_MS = 120_000L
        const val MAX_PENDING = 8
        const val MAX_PAYLOAD_CHARS = 16_000
        val ALLOWED_ACTIONS = setOf("tap", "swipe", "scroll", "back", "home", "input_text", "launch_app", "open_url")
    }
}
