package com.zexa.bridge

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Intent
import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject
import java.util.LinkedHashMap
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

class ActionExecutionUnknownException(message: String) : IllegalStateException(message)

class ZexaAccessibilityService : AccessibilityService() {
    @Volatile private var bridgeServer: BridgeServer? = null
    private val actionInterruptionGate = ActionInterruptionGate()
    private val actionApprovals = ActionApprovalRegistry()
    private val taskActionGrants = TaskActionGrantRegistry()
    // All reads and writes are guarded by the service monitor; insertion order gives FIFO eviction.
    private val actionResults = LinkedHashMap<String, JSONObject>()
    private val actionAudit by lazy {
        val prefs = getSharedPreferences("zexa_bridge", MODE_PRIVATE)
        ActionAuditStore(
            read = { prefs.getString("device_action_audit", null) },
            write = { value -> prefs.edit().putString("device_action_audit", value).apply() },
        )
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        markPendingApprovalsInterrupted()
        // A service restart invalidates in-memory approval tickets. Never revive
        // an approval that was waiting before the accessibility service reconnected.
        actionApprovals.clear()
        taskActionGrants.clear()
        refreshBridge()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Intentionally do not collect, store, or transmit events.
    }

    @Synchronized
    override fun onInterrupt() {
        // Invalidate work queued for the service looper before clearing one-use authority.
        // Approval/grant handlers never hold this monitor while waiting for that looper.
        actionInterruptionGate.invalidate()
        markPendingApprovalsInterrupted()
        actionApprovals.clear()
        taskActionGrants.clear()
    }

    private fun markPendingApprovalsInterrupted() {
        actionAudit.markPendingAsInterrupted(System.currentTimeMillis())
    }

    /** Persist expiry before any caller observes a missing approval ticket. */
    @Synchronized
    private fun recordExpiredApprovals() {
        actionApprovals.expireAndDrain(SystemClock.elapsedRealtime()).forEach { ticket ->
            val result = JSONObject()
                .put("ok", false)
                .put("status", "expired")
                .put("request_id", ticket.requestId)
            rememberActionResult(ticket.requestId, result)
            actionAudit.append(ActionAuditEntry(ticket.requestId, ticket.action, "expired", System.currentTimeMillis()))
        }
    }

    @Synchronized
    private fun invalidateBridgeSession() {
        // Stop is a session boundary: close active sockets and prevent any
        // approval/grant action queued on the service looper from starting later.
        actionInterruptionGate.invalidate()
        markPendingApprovalsInterrupted()
        actionApprovals.clear()
        taskActionGrants.clear()
        bridgeServer?.stop()
        bridgeServer = null
    }

    @Synchronized
    fun refreshBridge() {
        val enabled = getSharedPreferences("zexa_bridge", MODE_PRIVATE)
            .getBoolean("bridge_enabled", false)
        if (enabled) {
            if (bridgeServer?.isRunning != true) {
                invalidateBridgeSession()
                val token = getSharedPreferences("zexa_bridge", MODE_PRIVATE)
                    .getString("token", null) ?: return
                bridgeServer = BridgeServer(token, this).also { it.start() }
            }
        } else {
            invalidateBridgeSession()
        }
    }

    @Synchronized
    fun createTaskActionGrant(taskId: String, actions: Set<String>, ttlMs: Long, maxActions: Int): TaskActionGrant {
        require(bridgeServer?.isRunning == true) { "Enable the authenticated local bridge before creating a task grant." }
        require(BridgeSecurityRules.validTaskId(taskId)) { "Invalid task identifier." }
        val prefs = getSharedPreferences("zexa_bridge", MODE_PRIVATE)
        val deviceId = prefs.getString("device_id", null) ?: UUID.randomUUID().toString().also {
            prefs.edit().putString("device_id", it).apply()
        }
        val grant = taskActionGrants.create(
            taskId = taskId,
            deviceId = deviceId,
            actions = actions,
            nowElapsedMs = SystemClock.elapsedRealtime(),
            nowEpochMs = System.currentTimeMillis(),
            ttlMs = ttlMs,
            maxActions = maxActions,
        )
        actionAudit.append(ActionAuditEntry("grant-created-" + grant.grantId.take(48), "task_grant", "created", System.currentTimeMillis()))
        return grant
    }

    fun activeTaskActionGrants(): List<TaskActionGrant> =
        taskActionGrants.list(SystemClock.elapsedRealtime())

    fun revokeTaskActionGrant(grantId: String): Boolean {
        val revoked = taskActionGrants.revoke(grantId)
        if (revoked) actionAudit.append(ActionAuditEntry("grant-revoked-" + grantId.take(48), "task_grant", "revoked", System.currentTimeMillis()))
        return revoked
    }

    fun performGrantedAction(taskId: String, grantId: String, action: String, payload: JSONObject): JSONObject {
        val generation: Long
        val consumed: TaskActionGrant
        synchronized(this) {
            require(action in TaskActionGrantRegistry.GRANTABLE_ACTIONS) { "Action is not eligible for a task grant." }
            require(BridgeSecurityRules.validActionPayload(action, payload)) { "Invalid payload for the requested Android action." }
            val prefs = getSharedPreferences("zexa_bridge", MODE_PRIVATE)
            val deviceId = prefs.getString("device_id", null)
                ?: return JSONObject().put("ok", false).put("status", "grant_unavailable")
            consumed = taskActionGrants.consume(
                grantId, taskId, deviceId, action, SystemClock.elapsedRealtime()
            ) ?: return JSONObject().put("ok", false).put("status", "grant_scope_mismatch_or_expired")
            generation = actionInterruptionGate.current()
        }
        val result = try {
            val execution = onServiceThread {
                actionInterruptionGate.requireCurrent(generation)
                performOnServiceThread(action, payload)
            }
            execution.put("status", when {
                execution.optString("status") == "dispatched" -> "dispatched"
                execution.optBoolean("ok", false) -> "completed"
                else -> "failed"
            })
                .put("grant_id", grantId)
                .put("remaining_actions", consumed.remainingActions)
        } catch (error: ActionExecutionUnknownException) {
            JSONObject().put("ok", false).put("status", "execution_unknown")
                .put("grant_id", grantId)
                .put("error", error.message ?: "Execution result is unknown; do not retry automatically.")
                .put("remaining_actions", consumed.remainingActions)
        } catch (error: Exception) {
            JSONObject().put("ok", false).put("status", "failed")
                .put("grant_id", grantId)
                .put("error", error.message ?: "Action failed")
                .put("remaining_actions", consumed.remainingActions)
        }
        synchronized(this) {
            actionAudit.append(ActionAuditEntry("grant-action-" + grantId.take(28) + "-" + UUID.randomUUID().toString().take(12), action, result.optString("status", "failed"), System.currentTimeMillis()))
        }
        return result
    }

    @Synchronized
    fun queueActionForApproval(action: String, payload: JSONObject): JSONObject {
        recordExpiredApprovals()
        require(action in ActionApprovalRegistry.ALLOWED_ACTIONS) { "Device action is not allowlisted." }
        require(BridgeSecurityRules.validActionPayload(action, payload)) {
            "Invalid payload for the requested Android action."
        }
        val ticket = actionApprovals.create(action, payload.toString(), SystemClock.elapsedRealtime(), System.currentTimeMillis())
        actionAudit.append(ActionAuditEntry(ticket.requestId, ticket.action, "pending_approval", ticket.createdAtEpochMs))
        notifyApprovalNeeded(ticket)
        return JSONObject()
            .put("ok", true)
            .put("status", "pending_approval")
            .put("request_id", ticket.requestId)
            .put("expires_at_epoch_ms", ticket.expiresAtEpochMs)
    }

    private fun notifyApprovalNeeded(ticket: PendingDeviceAction) {
        try {
            if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) return
            val manager = NotificationManagerCompat.from(this)
            if (!manager.areNotificationsEnabled()) return
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val system = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                system.createNotificationChannel(
                    NotificationChannel(
                        APPROVAL_CHANNEL_ID,
                        "Device action approvals",
                        NotificationManager.IMPORTANCE_HIGH,
                    ).apply {
                        description = "Alerts that a device action is waiting for your review"
                    }
                )
            }
            val openApp = PendingIntent.getActivity(
                this,
                ticket.requestId.hashCode(),
                Intent(this, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                    putExtra(MainActivity.EXTRA_ACTION_APPROVAL_REQUEST_ID, ticket.requestId)
                },
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            val notification = NotificationCompat.Builder(this, APPROVAL_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("Zexa needs your approval")
                .setContentText("Review the " + ticket.action + " request in Device. Nothing runs until you approve.")
                .setContentIntent(openApp)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build()
            manager.notify(ticket.requestId.hashCode(), notification)
        } catch (_: Exception) {
            // Notification failures must never cancel or execute the queued action.
        }
    }

    fun pendingActionApprovals(): List<PendingDeviceAction> {
        recordExpiredApprovals()
        return actionApprovals.list(SystemClock.elapsedRealtime())
    }

    fun isActionPending(requestId: String): Boolean {
        recordExpiredApprovals()
        return actionApprovals.list(SystemClock.elapsedRealtime()).any { it.requestId == requestId }
    }

    fun approveAction(requestId: String): JSONObject {
        val ticket: PendingDeviceAction
        val generation: Long
        synchronized(this) {
            recordExpiredApprovals()
            ticket = actionApprovals.approve(requestId, SystemClock.elapsedRealtime())
                ?: return JSONObject().put("ok", false).put("status", "expired_or_not_pending")
            generation = actionInterruptionGate.current()
            val executing = JSONObject()
                .put("ok", true)
                .put("status", "executing")
                .put("request_id", ticket.requestId)
            rememberActionResult(ticket.requestId, executing)
            actionAudit.append(ActionAuditEntry(ticket.requestId, ticket.action, "executing", System.currentTimeMillis()))
        }
        val result = try {
            val execution = onServiceThread {
                actionInterruptionGate.requireCurrent(generation)
                performOnServiceThread(ticket.action, JSONObject(ticket.payloadJson))
            }
            execution
                .put("status", when {
                    execution.optString("status") == "dispatched" -> "dispatched"
                    execution.optBoolean("ok", false) -> "completed"
                    else -> "failed"
                })
                .put("request_id", ticket.requestId)
        } catch (error: ActionExecutionUnknownException) {
            JSONObject()
                .put("ok", false)
                .put("status", "execution_unknown")
                .put("request_id", ticket.requestId)
                .put("error", error.message ?: "Execution result is unknown; do not retry automatically.")
        } catch (error: Exception) {
            JSONObject()
                .put("ok", false)
                .put("status", "failed")
                .put("request_id", ticket.requestId)
                .put("error", error.message ?: "Action failed")
        }
        synchronized(this) {
            rememberActionResult(ticket.requestId, result)
            actionAudit.append(ActionAuditEntry(ticket.requestId, ticket.action, result.optString("status", "failed"), System.currentTimeMillis()))
        }
        return result
    }

    @Synchronized
    fun denyAction(requestId: String): JSONObject {
        recordExpiredApprovals()
        val ticket = actionApprovals.deny(requestId, SystemClock.elapsedRealtime())
        val denied = ticket != null
        val result = JSONObject()
            .put("ok", false)
            .put("status", if (denied) "denied" else "expired_or_not_pending")
            .put("request_id", requestId)
        if (ticket != null) {
            rememberActionResult(requestId, result)
            actionAudit.append(ActionAuditEntry(requestId, ticket.action, "denied", System.currentTimeMillis()))
        }
        return result
    }

    @Synchronized
    fun actionAuditHistory(): List<ActionAuditEntry> {
        recordExpiredApprovals()
        return actionAudit.list()
    }

    @Synchronized
    fun actionResult(requestId: String): JSONObject? {
        recordExpiredApprovals()
        actionResults[requestId]?.let { return JSONObject(it.toString()) }
        val pending = actionApprovals.list(SystemClock.elapsedRealtime())
            .firstOrNull { it.requestId == requestId }
            ?: return null
        return JSONObject()
            .put("ok", true)
            .put("status", "pending_approval")
            .put("request_id", pending.requestId)
    }

    @Synchronized
    private fun rememberActionResult(requestId: String, result: JSONObject) {
        actionResults[requestId] = JSONObject(result.toString())
        while (actionResults.size > MAX_ACTION_RESULTS) {
            val oldest = actionResults.entries.iterator().next().key
            actionResults.remove(oldest)
        }
    }

    fun isScreenAccessEnabled(): Boolean =
        BridgeSecurityRules.screenAccessEnabled(
            getSharedPreferences("zexa_bridge", MODE_PRIVATE).all["screen_access_enabled"]
        )

    fun statusJson(): JSONObject = JSONObject()
        .put("ok", true)
        .put("accessibility_enabled", true)
        .put("bridge_enabled", bridgeServer?.isRunning == true)

    fun screenJson(): JSONObject = onServiceThread {
        // Re-check permission on the service looper immediately before reading the
        // active window. The UI toggle also runs on this looper, so it cannot race
        // between this check and snapshot traversal.
        if (!isScreenAccessEnabled()) {
            JSONObject()
                .put("ok", false)
                .put("screen_access_disabled", true)
                .put("error", "Screen access is disabled in Zexa settings.")
        } else {
            buildScreenSnapshot()
        }
    }

    private fun buildScreenSnapshot(): JSONObject {
        val root = rootInActiveWindow ?: return JSONObject()
            .put("ok", true).put("package", "").put("nodes", JSONArray())
        val nodes = JSONArray()
        var count = 0
        fun hasOtpLabelChild(parent: AccessibilityNodeInfo): Boolean {
            for (index in 0 until minOf(parent.childCount, 150)) {
                val child = parent.getChild(index) ?: continue
                val hasLabel = try {
                    ScreenRedactionRules.isOtpLabel(
                        className = child.className?.toString()?.take(160) ?: "",
                        viewId = child.viewIdResourceName?.take(200) ?: "",
                        hint = child.hintText?.toString()?.take(300) ?: "",
                        text = child.text?.toString()?.take(500) ?: "",
                        description = child.contentDescription?.toString()?.take(300) ?: "",
                    )
                } finally {
                    child.recycle()
                }
                if (hasLabel) return true
            }
            return false
        }
        fun visit(node: AccessibilityNodeInfo?, depth: Int, sensitiveOtpContext: Boolean = false) {
            if (node == null || depth > 12 || count >= 150) return
            count++
            val bounds = Rect()
            node.getBoundsInScreen(bounds)
            val className = node.className?.toString()?.take(160) ?: ""
            val viewId = node.viewIdResourceName?.take(200) ?: ""
            val text = node.text?.toString()?.take(500) ?: ""
            val description = node.contentDescription?.toString()?.take(300) ?: ""
            val hint = node.hintText?.toString()?.take(300) ?: ""
            val redacted = ScreenRedactionRules.shouldRedact(
                isPassword = node.isPassword,
                isEditable = node.isEditable,
                className = className,
                viewId = viewId,
                hint = hint,
                text = text,
                description = description,
                sensitiveOtpContext = sensitiveOtpContext,
            )
            val item = JSONObject()
                .put("index", count - 1)
                .put("class", className)
                .put("view_id", viewId)
                .put("text", if (redacted) "" else text)
                .put("description", if (redacted) "" else description)
                .put("redacted", redacted)
                .put("clickable", node.isClickable)
                .put("editable", node.isEditable)
                .put("password", node.isPassword)
                .put("bounds", JSONObject()
                    .put("left", bounds.left).put("top", bounds.top)
                    .put("right", bounds.right).put("bottom", bounds.bottom))
            nodes.put(item)
            val childOtpContext = sensitiveOtpContext || hasOtpLabelChild(node)
            // Bound child retrieval as well as emitted nodes; hostile or malformed
            // accessibility trees must not force unbounded traversal work.
            val childLimit = minOf(node.childCount, 150 - count)
            for (i in 0 until childLimit) {
                val child = node.getChild(i)
                try {
                    visit(child, depth + 1, childOtpContext)
                } finally {
                    child?.recycle()
                }
            }
        }
        return try {
            visit(root, 0)
            JSONObject()
                .put("ok", true)
                .put("package", root.packageName?.toString() ?: "")
                .put("nodes", nodes)
        } finally {
            root.recycle()
        }
    }

    fun perform(action: String, payload: JSONObject): JSONObject =
        onServiceThread { performOnServiceThread(action, payload) }

    private fun performOnServiceThread(action: String, payload: JSONObject): JSONObject {
        require(BridgeSecurityRules.validActionPayload(action, payload)) {
            "Invalid payload for the requested Android action."
        }
        return when (action) {
            "tap" -> {
                val x = payload.optDouble("x", Double.NaN)
                val y = payload.optDouble("y", Double.NaN)
                require(BridgeSecurityRules.coordinate(x) && BridgeSecurityRules.coordinate(y))
                val path = Path().apply { moveTo(x.toFloat(), y.toFloat()) }
                dispatch(path, 80)
            }
            "swipe", "scroll" -> {
                val x1 = payload.optDouble("x1", Double.NaN)
                val y1 = payload.optDouble("y1", Double.NaN)
                val x2 = payload.optDouble("x2", Double.NaN)
                val y2 = payload.optDouble("y2", Double.NaN)
                val duration = payload.optLong("duration_ms", 450L)
                require(listOf(x1, y1, x2, y2).all { BridgeSecurityRules.coordinate(it) })
                require(BridgeSecurityRules.gestureDuration(duration))
                val path = Path().apply {
                    moveTo(x1.toFloat(), y1.toFloat())
                    lineTo(x2.toFloat(), y2.toFloat())
                }
                dispatch(path, duration)
            }
            "back" -> JSONObject().put("ok", performGlobalAction(GLOBAL_ACTION_BACK))
            "home" -> JSONObject().put("ok", performGlobalAction(GLOBAL_ACTION_HOME))
            "input_text" -> {
                val text = payload.optString("text", "")
                require(text.isNotBlank() && text.length <= 500)
                val root = rootInActiveWindow ?: error("No active input window.")
                val target = try {
                    root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
                        ?: error("No focused input field.")
                } finally {
                    root.recycle()
                }
                try {
                    require(target.isEditable && !target.isPassword) {
                        "Focused field is not an eligible non-password input."
                    }
                    val args = Bundle().apply {
                        putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
                    }
                    val ok = target.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
                    JSONObject().put("ok", ok)
                } finally {
                    target.recycle()
                }
            }
            "launch_app" -> {
                val packageName = payload.optString("package_name", "")
                require(BridgeSecurityRules.packageName(packageName))
                val launch = packageManager.getLaunchIntentForPackage(packageName)
                    ?: error("No launchable app for that package.")
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(launch)
                JSONObject().put("ok", true)
            }
            "open_url" -> {
                val url = payload.optString("url", "")
                require(BridgeSecurityRules.safeWebUrl(url))
                val view = Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(view)
                JSONObject().put("ok", true)
            }
            else -> error("Action is not allowlisted.")
        }
    }

    /**
     * AccessibilityService APIs and AccessibilityNodeInfo traversal are executed
     * on the Android main/service looper even when an HTTP client calls the
     * bridge from a worker thread.
     */
    private fun <T> onServiceThread(block: () -> T): T {
        if (Looper.myLooper() == Looper.getMainLooper()) return block()
        val completed = CountDownLatch(1)
        val outcome = AtomicReference<Result<T>?>(null)
        val gate = Any()
        var cancelledBeforeStart = false
        var started = false
        val handler = Handler(Looper.getMainLooper())
        if (!handler.post {
                synchronized(gate) {
                    if (cancelledBeforeStart) {
                        completed.countDown()
                        return@post
                    }
                    started = true
                }
                outcome.set(runCatching(block))
                completed.countDown()
            }
        ) {
            error("Could not schedule work on the Android service thread.")
        }
        try {
            if (!completed.await(10, TimeUnit.SECONDS)) {
                synchronized(gate) {
                    if (!started) {
                        cancelledBeforeStart = true
                        error("Android service thread did not start the requested operation in time.")
                    }
                }
                if (!completed.await(20, TimeUnit.SECONDS)) {
                    throw ActionExecutionUnknownException(
                        "Android operation started but did not report a result in time; do not retry automatically."
                    )
                }
            }
        } catch (interrupted: InterruptedException) {
            Thread.currentThread().interrupt()
            val operationStarted = synchronized(gate) { started }
            if (operationStarted) {
                throw ActionExecutionUnknownException(
                    "Android operation started before the wait was interrupted; its result is unknown. Do not retry automatically."
                )
            }
            throw IllegalStateException("Interrupted while waiting for the Android service thread.", interrupted)
        }
        return outcome.get()?.getOrThrow()
            ?: error("Android service thread returned no operation result.")
    }

    private fun dispatch(path: Path, duration: Long): JSONObject {
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, duration))
            .build()
        val accepted = dispatchGesture(gesture, null, null)
        return JSONObject()
            .put("ok", accepted)
            .put("status", if (accepted) "dispatched" else "failed")
    }

    @Synchronized
    override fun onDestroy() {
        actionInterruptionGate.invalidate()
        markPendingApprovalsInterrupted()
        actionApprovals.clear()
        taskActionGrants.clear()
        bridgeServer?.stop()
        bridgeServer = null
        instance = null
        super.onDestroy()
    }

    companion object {
        private const val MAX_ACTION_RESULTS = 64
        private const val APPROVAL_CHANNEL_ID = "zexa_action_approvals"
        @Volatile var instance: ZexaAccessibilityService? = null
            private set
    }
}
