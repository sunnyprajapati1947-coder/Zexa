package com.zexa.bridge

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.security.SecureRandom

class MainActivity : Activity() {
    private lateinit var bridgeButton: Button
    private lateinit var bridgeStatus: TextView
    private lateinit var content: LinearLayout

    private fun preferences() = getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE)

    private fun getOrCreateToken(): String {
        val existing = preferences().getString("token", null)
        if (!existing.isNullOrBlank() && BridgeSecurityRules.validBridgeToken(existing)) return existing
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        val token = bytes.joinToString("") { "%02x".format(it) }
        preferences().edit().putString("token", token).apply()
        return token
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        getOrCreateToken()
        val page = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(28), dp(22), dp(28))
            setBackgroundColor(0xFF101116.toInt())
        }
        page.addView(root)
        root.addView(TextView(this).apply {
            text = "ZEXA"
            textSize = 30f
            setTextColor(0xFFF4F4F5.toInt())
            letterSpacing = 0.16f
        })
        root.addView(TextView(this).apply {
            text = "PERSONAL AI WORKSPACE"
            textSize = 11f
            letterSpacing = 0.14f
            setTextColor(0xFF9CA3AF.toInt())
            setPadding(0, dp(4), 0, dp(22))
        })

        content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        root.addView(content, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        showHome()

        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, dp(18), 0, 0)
        }
        listOf("Home", "Chat", "Brain", "Tasks", "Memory", "Device").forEach { label ->
            nav.addView(Button(this).apply {
                text = label
                textSize = 10f
                setOnClickListener { showSection(label) }
            }, LinearLayout.LayoutParams(0, dp(46), 1f))
        }
        root.addView(nav)
        setContentView(page)
    }

    private fun showSection(section: String) {
        when (section) {
            "Home" -> showHome()
            "Chat" -> showStatusPage("Chat", "Native chat interface foundation", "The Android chat screen is being connected to the Zexa brain. No demo replies are generated or presented as real AI output.")
            "Brain" -> showStatusPage("Brain", "Qwen runtime integration pending", "The app does not yet load a local GGUF model. Model selection, storage checks, inference and secure online-provider setup must be integrated before this is marked ready.")
            "Tasks" -> showStatusPage("Tasks", "Native task centre pending", "The current Python task queue has not yet been migrated to Android-native persistent scheduling and notifications.")
            "Memory" -> showStatusPage("Memory", "Private memory centre pending", "Conversation history and explicit memory controls are not yet connected to Android storage.")
            "Device" -> showDevice()
        }
    }

    private fun showHome() {
        content.removeAllViews()
        addHeading("Your assistant, in progress")
        addCard("APP STATUS", "Android foundation active", "This build is the first native workspace shell. Brain, chat, voice, memory and tasks are not falsely marked as ready.")
        addCard("AI BRAIN", "Not connected", "Qwen on-device inference is the next core integration.")
        addCard("VOICE", "Not connected", "Microphone capture and speech output will be added with visible controls.")
        addCard("MEMORY & TASKS", "Migration pending", "These modules need Android-native storage and scheduling.")
        addCard("DEVICE HAND", "Optional and OFF by default", "Accessibility access is separate from AI chat and remains user-controlled.")
        addButton("Open device settings") { showDevice() }
    }

    private fun showStatusPage(title: String, status: String, detail: String) {
        content.removeAllViews()
        addHeading(title)
        addCard("CURRENT STATUS", status, detail)
        addCard("INTEGRATION RULE", "No fake completion", "A module will be marked ready only after its real implementation and tests are in this app.")
    }

    private fun showDevice() {
        content.removeAllViews()
        addHeading("Device connection")
        addCard("ACCESSIBILITY", if (ZexaAccessibilityService.instance != null) "Service connected" else "Permission required", "Enable the Zexa Accessibility Bridge only if you want the optional device-control feature.")
        content.addView(Button(this).apply {
            text = "Open Accessibility Settings"
            setOnClickListener { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        })
        bridgeStatus = TextView(this).apply {
            textSize = 13f
            setTextColor(0xFFE5E7EB.toInt())
            setPadding(0, dp(16), 0, dp(8))
        }
        content.addView(bridgeStatus)
        bridgeButton = Button(this).apply { setOnClickListener { toggleBridge() } }
        content.addView(bridgeButton)
        content.addView(Button(this).apply {
            text = "Copy local bridge token"
            setOnClickListener {
                val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText("Zexa local bridge token", getOrCreateToken()))
                Toast.makeText(this@MainActivity, "Token copied. Keep it private.", Toast.LENGTH_LONG).show()
            }
        })
        addCard("SAFETY", "Remote actions are temporarily disabled", "The bridge currently has no native per-action confirmation screen. Requests to perform device actions are denied until that approval flow is implemented. Screen snapshots may contain private information; do not share them.")
        refreshBridgeUi()
    }

    private fun toggleBridge() {
        val enabled = !preferences().getBoolean("bridge_enabled", false)
        if (enabled && ZexaAccessibilityService.instance == null) {
            Toast.makeText(this, "Enable Zexa Accessibility Bridge in Android Settings first.", Toast.LENGTH_LONG).show()
            return
        }
        preferences().edit().putBoolean("bridge_enabled", enabled).apply()
        ZexaAccessibilityService.instance?.refreshBridge()
        refreshBridgeUi()
    }

    private fun refreshBridgeUi() {
        if (!::bridgeButton.isInitialized) return
        val enabled = preferences().getBoolean("bridge_enabled", false)
        bridgeButton.text = if (enabled) "Stop local bridge" else "Start local bridge"
        if (::bridgeStatus.isInitialized) {
            bridgeStatus.text = if (enabled) "Bridge requested ON. Check service readiness." else "Bridge is OFF."
        }
    }

    private fun addHeading(value: String) {
        content.addView(TextView(this).apply {
            text = value
            textSize = 23f
            setTextColor(0xFFF9FAFB.toInt())
            setPadding(0, 0, 0, dp(14))
        })
    }

    private fun addCard(label: String, value: String, detail: String) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            setBackgroundColor(0xFF20232B.toInt())
        }
        card.addView(TextView(this).apply {
            text = label
            textSize = 10f
            letterSpacing = 0.12f
            setTextColor(0xFF9CA3AF.toInt())
        })
        card.addView(TextView(this).apply {
            text = value
            textSize = 17f
            setTextColor(0xFFF9FAFB.toInt())
            setPadding(0, dp(5), 0, dp(5))
        })
        card.addView(TextView(this).apply {
            text = detail
            textSize = 13f
            setTextColor(0xFFD1D5DB.toInt())
        })
        val params = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        params.bottomMargin = dp(12)
        content.addView(card, params)
    }

    private fun addButton(label: String, action: () -> Unit) {
        content.addView(Button(this).apply {
            text = label
            setOnClickListener { action() }
        })
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    override fun onResume() {
        super.onResume()
        ZexaAccessibilityService.instance?.refreshBridge()
        if (::bridgeButton.isInitialized) refreshBridgeUi()
    }
}
