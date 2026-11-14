package com.zexa.bridge

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Intent
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject

class ZexaAccessibilityService : AccessibilityService() {
    @Volatile private var bridgeServer: BridgeServer? = null

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        refreshBridge()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Intentionally do not collect, store, or transmit events.
    }

    override fun onInterrupt() = Unit

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
            bridgeServer?.stop()
            bridgeServer = null
        }
    }

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
        bridgeServer?.stop()
        bridgeServer = null
        instance = null
        super.onDestroy()
    }

    companion object {
        @Volatile var instance: ZexaAccessibilityService? = null
            private set
    }
}
