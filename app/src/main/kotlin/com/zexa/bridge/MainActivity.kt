package com.zexa.bridge

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.security.SecureRandom

class MainActivity : Activity() {
    private lateinit var tokenView: TextView
    private lateinit var bridgeButton: Button

    private fun preferences() = getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE)

    private fun getOrCreateToken(): String {
        val existing = preferences().getString("token", null)
        if (!existing.isNullOrBlank()) return existing
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        val token = bytes.joinToString("") { "%02x".format(it) }
        preferences().edit().putString("token", token).apply()
        return token
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(24, 32, 24, 24)
        }
        root.addView(TextView(this).apply {
            text = "Zexa Accessibility Bridge"
            textSize = 24f
        })
        root.addView(TextView(this).apply {
            text = "Local-only connection: 127.0.0.1:8765\nThe bridge is OFF by default. Enable Android Accessibility manually, then start the local bridge here."
            textSize = 15f
            setPadding(0, 18, 0, 18)
        })
        root.addView(Button(this).apply {
            text = "Open Accessibility Settings"
            setOnClickListener { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        })
        tokenView = TextView(this).apply {
            text = "Bearer token (keep private):\n${getOrCreateToken()}"
            textSize = 13f
            setTextIsSelectable(true)
            setPadding(0, 20, 0, 12)
        }
        root.addView(tokenView, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        root.addView(Button(this).apply {
            text = "Copy token"
            setOnClickListener {
                val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText("Zexa Bridge token", getOrCreateToken()))
            }
        })
        bridgeButton = Button(this).apply {
            setOnClickListener { toggleBridge() }
        }
        root.addView(bridgeButton)
        root.addView(TextView(this).apply {
            text = "Security: the server binds only to 127.0.0.1. The token is required for every request. Password-field text is never returned. Device actions are limited to an allowlist and must be explicitly approved by the connected Zexa client."
            textSize = 13f
            setPadding(0, 24, 0, 0)
        })
        setContentView(root)
        refreshButton()
    }

    private fun toggleBridge() {
        val enabled = !preferences().getBoolean("bridge_enabled", false)
        preferences().edit().putBoolean("bridge_enabled", enabled).apply()
        ZexaAccessibilityService.instance?.refreshBridge()
        refreshButton()
    }

    private fun refreshButton() {
        val enabled = preferences().getBoolean("bridge_enabled", false)
        bridgeButton.text = if (enabled) "Stop local bridge" else "Start local bridge"
    }

    override fun onResume() {
        super.onResume()
        refreshButton()
    }
}
