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
import java.util.concurrent.ConcurrentHashMap
import java.util.UUID

class ZexaAccessibilityService : AccessibilityService() {
    @Volatile private var bridgeServer: BridgeServer? = null
    private val actionApprovals = ActionApprovalRegistry()
    private val taskActionGrants = TaskActionGrantRegistry()
    private val actionResults = ConcurrentHashMap<String, JSONObject>()
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

    override fun onInterrupt() {
        markPendingApprovalsInterrupted()
        actionApprovals.clear()
        taskActionGrants.clear()
    }

    private fun markPendingApprovalsInterrupted() {
        actionAudit.markPendingAsInterrupted(System.currentTimeMillis())
    }

    @Synchronized
    fun refreshBridge() {
        val enabled = getSharedPreferences("zexa_bridge", MODE_PRIVATE)
            .getBoolean("bridge_enabled", false)
        if (enabled) {
            if (bridgeServer?.isRunning != true) {
                bridgeServer?.stop()
                val token = getSharedPreferences("zexa_bridge", MODE_PRIVATE)
                    .getString("token", null) ?: return
                bridgeServer = BridgeServer(token, this).also { it.start() }
            }
        } else {
            markPendingApprovalsInterrupted()
            bridgeServer?.stop()
            bridgeServer = null
            actionApprovals.clear()
            taskActionGrants.clear()
        }
    }

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
        actionAudit.append(ActionAuditEntry("grant-" + grant.grantId.take(48), "task_grant", "created", System.currentTimeMillis()))
        return grant
    }

    fun activeTaskActionGrants(): List<TaskActionGrant> =
        taskActionGrants.list(SystemClock.elapsedRealtime())

    fun revokeTaskActionGrant(grantId: String): Boolean {
        val revoked = taskActionGrants.revoke(grantId)
        if (revoked) actionAudit.append(ActionAuditEntry("grant-" + grantId.take(48), "task_grant", "revoked", System.currentTimeMillis()))
        return revoked
    }

    @Synchronized
    fun performGrantedAction(taskId: String, grantId: String, action: String, payload: JSONObject): JSONObject {
        require(action in TaskActionGrantRegistry.GRANTABLE_ACTIONS) { "Action is not eligible for a task grant." }
        require(BridgeSecurityRules.validActionPayload(action, payload)) { "Invalid payload for the requested Android action." }
        val prefs = getSharedPreferences("zexa_bridge", MODE_PRIVATE)
        val deviceId = prefs.getString("device_id", null)
            ?: return JSONObject().put("ok", false).put("status", "grant_unavailable")
        val consumed = taskActionGrants.consume(
            grantId, taskId, deviceId, action, SystemClock.elapsedRealtime()
        ) ?: return JSONObject().put("ok", false).put("status", "grant_scope_mismatch_or_expired")
        val result = try {
            perform(action, payload).put("status", "completed")
                .put("grant_id", grantId)
                .put("remaining_actions", consumed.remainingActions)
        } catch (error: Exception) {
            JSONObject().put("ok", false).put("status", "failed")
                .put("grant_id", grantId)
                .put("error", error.message ?: "Action failed")
                .put("remaining_actions", consumed.remainingActions)
        }
        actionAudit.append(ActionAuditEntry("grant-" + grantId.take(48), action, result.optString("status", "failed"), System.currentTimeMillis()))
        return result
    }

    fun queueActionForApproval(action: String, payload: JSONObject): JSONObject {
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

    fun pendingActionApprovals(): List<PendingDeviceAction> =
        actionApprovals.list(SystemClock.elapsedRealtime())

    fun isActionPending(requestId: String): Boolean =
        actionApprovals.list(SystemClock.elapsedRealtime()).any { it.requestId == requestId }

    @Synchronized
    fun approveAction(requestId: String): JSONObject {
        val ticket = actionApprovals.approve(requestId, SystemClock.elapsedRealtime())
            ?: return JSONObject().put("ok", false).put("status", "expired_or_not_pending")
        val result = try {
            val execution = perform(ticket.action, JSONObject(ticket.payloadJson))
            execution
                .put("status", if (execution.optBoolean("ok", false)) "completed" else "failed")
                .put("request_id", ticket.requestId)
        } catch (error: Exception) {
            JSONObject()
                .put("ok", false)
                .put("status", "failed")
                .put("request_id", ticket.requestId)
                .put("error", error.message ?: "Action failed")
        }
        rememberActionResult(ticket.requestId, result)
        actionAudit.append(ActionAuditEntry(ticket.requestId, ticket.action, result.optString("status", "failed"), System.currentTimeMillis()))
        return result
    }

    fun denyAction(requestId: String): JSONObject {
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

    fun actionAuditHistory(): List<ActionAuditEntry> = actionAudit.list()

    fun actionResult(requestId: String): JSONObject? =
        actionResults[requestId]?.let { JSONObject(it.toString()) }

    @Synchronized
    private fun rememberActionResult(requestId: String, result: JSONObject) {
        actionResults[requestId] = JSONObject(result.toString())
        while (actionResults.size > MAX_ACTION_RESULTS) {
            val oldest = actionResults.keys().nextElement()
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

    fun screenJson(): JSONObject {
        val root = rootInActiveWindow ?: return JSONObject()
            .put("ok", true).put("package", "").put("nodes", JSONArray())
        val nodes = JSONArray()
        var count = 0
        fun visit(node: AccessibilityNodeInfo?, depth: Int) {
            if (node == null || depth > 12 || count >= 150) return
            count++
            val bounds = Rect()
            node.getBoundsInScreen(bounds)
            val item = JSONObject()
                .put("index", count - 1)
                .put("class", node.className?.toString()?.take(160) ?: "")
                .put("view_id", node.viewIdResourceName?.take(200) ?: "")
                .put("text", if (node.isPassword) "" else node.text?.toString()?.take(500) ?: "")
                .put("description", if (node.isPassword) "" else node.contentDescription?.toString()?.take(300) ?: "")
                .put("clickable", node.isClickable)
                .put("editable", node.isEditable)
                .put("password", node.isPassword)
                .put("bounds", JSONObject()
                    .put("left", bounds.left).put("top", bounds.top)
                    .put("right", bounds.right).put("bottom", bounds.bottom))
            nodes.put(item)
            for (i in 0 until node.childCount) {
                val child = node.getChild(i)
                visit(child, depth + 1)
                child?.recycle()
            }
        }
        visit(root, 0)
        val result = JSONObject()
            .put("ok", true)
            .put("package", root.packageName?.toString() ?: "")
            .put("nodes", nodes)
        root.recycle()
        return result
    }

    fun perform(action: String, payload: JSONObject): JSONObject {
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
                val target = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
                root.recycle()
                require(target != null && target.isEditable && !target.isPassword)
                val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text) }
                val ok = target.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
                target.recycle()
                JSONObject().put("ok", ok)
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

    private fun dispatch(path: Path, duration: Long): JSONObject {
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, duration))
            .build()
        return JSONObject().put("ok", dispatchGesture(gesture, null, null))
    }

    override fun onDestroy() {
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
