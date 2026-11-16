package com.zexa.bridge

import java.util.UUID
import java.util.Collections

/**
 * In-memory, bounded grants for non-committing navigation actions.
 *
 * Coordinate taps and text entry are deliberately excluded: a tap may submit,
 * delete, purchase, or otherwise commit an action depending on the current UI.
 * The device ID supplied to create() must be generated and owned by the
 * Android service, never copied from an untrusted request. Grants are
 * process-local and must be cleared whenever the service is interrupted,
 * disabled, reconnected, or destroyed.
 */
data class TaskActionGrant(
    val grantId: String,
    val taskId: String,
    val deviceId: String,
    val allowedActions: Set<String>,
    val createdAtEpochMs: Long,
    val expiresAtEpochMs: Long,
    val expiresAtElapsedRealtimeMs: Long,
    val maxActions: Int,
    val remainingActions: Int,
)

class TaskActionGrantRegistry(
    private val maxTtlMs: Long = DEFAULT_TTL_MS,
    private val maxGrants: Int = MAX_GRANTS,
    private val idFactory: () -> String = { UUID.randomUUID().toString() },
) {
    private data class Entry(
        val grant: TaskActionGrant,
        var remaining: Int,
    )

    private val grants = LinkedHashMap<String, Entry>()
    private var lastObservedElapsedMs = 0L

    init {
        require(maxTtlMs in MIN_TTL_MS..MAX_TTL_MS)
        require(maxGrants in 1..MAX_GRANTS)
    }

    @Synchronized
    fun create(
        taskId: String,
        deviceId: String,
        actions: Set<String>,
        nowElapsedMs: Long,
        nowEpochMs: Long,
        ttlMs: Long = DEFAULT_TTL_MS,
        maxActions: Int = DEFAULT_ACTIONS,
    ): TaskActionGrant {
        require(validIdentifier(taskId) && validIdentifier(deviceId)) {
            "Task and device identifiers must be valid."
        }
        require(actions.isNotEmpty() && actions.size <= GRANTABLE_ACTIONS.size &&
            actions.all { it in GRANTABLE_ACTIONS }) {
            "Task grant contains an empty or non-grantable action set."
        }
        require(ttlMs in MIN_TTL_MS..maxTtlMs) { "Task grant duration is outside the allowed range." }
        require(maxActions in 1..MAX_ACTIONS) { "Task grant action budget is outside the allowed range." }
        require(nowElapsedMs >= 0L && nowElapsedMs <= Long.MAX_VALUE - ttlMs) {
            "Invalid monotonic task-grant timestamp."
        }
        require(nowEpochMs >= 0L && nowEpochMs <= Long.MAX_VALUE - ttlMs) {
            "Invalid task-grant timestamp."
        }

        val effectiveNow = observeTime(nowElapsedMs)
        expire(effectiveNow)
        require(grants.size < maxGrants) { "Too many active task grants." }

        val id = idFactory()
        require(validIdentifier(id) && !grants.containsKey(id)) {
            "Could not create a unique task grant."
        }

        val grant = TaskActionGrant(
            grantId = id,
            taskId = taskId,
            deviceId = deviceId,
            allowedActions = Collections.unmodifiableSet(actions.toSet()),
            createdAtEpochMs = nowEpochMs,
            expiresAtEpochMs = nowEpochMs + ttlMs,
            expiresAtElapsedRealtimeMs = effectiveNow + ttlMs,
            maxActions = maxActions,
            remainingActions = maxActions,
        )
        grants[id] = Entry(grant, maxActions)
        return grant
    }

    /** Consume one operation only when grant, task, device, action and expiry all match. */
    @Synchronized
    fun consume(
        grantId: String,
        taskId: String,
        deviceId: String,
        action: String,
        nowElapsedMs: Long,
    ): TaskActionGrant? {
        val effectiveNow = observeTime(nowElapsedMs)
        expire(effectiveNow)
        val entry = grants[grantId] ?: return null
        val grant = entry.grant
        if (grant.taskId != taskId || grant.deviceId != deviceId ||
            action !in grant.allowedActions || entry.remaining <= 0
        ) return null

        entry.remaining -= 1
        val updated = grant.copy(remainingActions = entry.remaining)
        if (entry.remaining == 0) grants.remove(grantId)
        return updated
    }

    @Synchronized
    fun list(nowElapsedMs: Long): List<TaskActionGrant> {
        val effectiveNow = observeTime(nowElapsedMs)
        expire(effectiveNow)
        return grants.values.map { it.grant.copy(remainingActions = it.remaining) }
    }

    @Synchronized
    fun revoke(grantId: String): Boolean = grants.remove(grantId) != null

    @Synchronized
    fun clear() = grants.clear()

    private fun observeTime(nowElapsedMs: Long): Long {
        require(nowElapsedMs >= 0L) { "Invalid monotonic task-grant timestamp." }
        if (nowElapsedMs > lastObservedElapsedMs) lastObservedElapsedMs = nowElapsedMs
        return lastObservedElapsedMs
    }

    private fun expire(nowElapsedMs: Long) {
        val iterator = grants.values.iterator()
        while (iterator.hasNext()) {
            if (iterator.next().grant.expiresAtElapsedRealtimeMs <= nowElapsedMs) iterator.remove()
        }
    }

    private fun validIdentifier(value: String): Boolean =
        value.matches(Regex("^[A-Za-z0-9._:-]{1,64}$"))

    companion object {
        const val MIN_TTL_MS = 1_000L
        const val DEFAULT_TTL_MS = 5 * 60_000L
        const val MAX_TTL_MS = 10 * 60_000L
        const val MAX_GRANTS = 4
        const val DEFAULT_ACTIONS = 30
        const val MAX_ACTIONS = 100
        val GRANTABLE_ACTIONS = setOf("swipe", "scroll", "back", "home", "launch_app", "open_url")
    }
}
