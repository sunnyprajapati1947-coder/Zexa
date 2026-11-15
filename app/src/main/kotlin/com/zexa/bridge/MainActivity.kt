package com.zexa.bridge

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import android.database.Cursor
import android.provider.OpenableColumns
import java.io.File
import java.security.SecureRandom

class MainActivity : Activity() {
    private lateinit var bridgeButton: Button
    private lateinit var bridgeStatus: TextView
    private lateinit var content: LinearLayout
    private var brainStatus: TextView? = null
    private var modelImportButton: Button? = null
    private var modelLoadButton: Button? = null
    private var inferenceButton: Button? = null
    private var inferencePrompt: EditText? = null
    private var inferenceOutput: TextView? = null
    @Volatile private var nativeModelLoaded = false
    private val modelStore by lazy { LocalModelStore(File(filesDir, "models")) }
    private val modelPickerRequest = 4107

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
            "Brain" -> showBrain()
            "Tasks" -> showStatusPage("Tasks", "Native task centre pending", "The current Python task queue has not yet been migrated to Android-native persistent scheduling and notifications.")
            "Memory" -> showStatusPage("Memory", "Private memory centre pending", "Conversation history and explicit memory controls are not yet connected to Android storage.")
            "Device" -> showDevice()
        }
    }

    private fun showHome() {
        content.removeAllViews()
        addHeading("Your assistant, in progress")
        addCard("APP STATUS", "Android foundation active", "This build is the first native workspace shell. Brain, chat, voice, memory and tasks are not falsely marked as ready.")
        addCard("AI BRAIN", "Native Qwen integration under validation", "GGUF import and llama.cpp JNI inference code are in place; CI and real-device inference still need verification.")
        addCard("VOICE", "Not connected", "Microphone capture and speech output will be added with visible controls.")
        addCard("MEMORY & TASKS", "Migration pending", "These modules need Android-native storage and scheduling.")
        addCard("DEVICE HAND", "Optional and OFF by default", "Accessibility access is separate from AI chat and remains user-controlled.")
        addButton("Open device settings") { showDevice() }
    }


    private fun showBrain() {
        content.removeAllViews()
        addHeading("AI brain")
        addCard("INFERENCE", "Native runtime integration — validation pending", "Import a GGUF model, load it into memory, then run a single-turn local inference test. Successful import alone does not prove inference works.")
        brainStatus = TextView(this).apply {
            textSize = 13f
            setTextColor(0xFFD1D5DB.toInt())
            setPadding(0, dp(8), 0, dp(12))
        }
        content.addView(brainStatus)
        modelImportButton = Button(this).apply {
            text = "Import Qwen GGUF model"
            setOnClickListener { openModelPicker() }
        }
        content.addView(modelImportButton)
        modelLoadButton = Button(this).apply {
            text = "Load model into memory"
            isEnabled = false
            setOnClickListener { loadLocalModel() }
        }
        content.addView(modelLoadButton)
        inferencePrompt = EditText(this).apply {
            hint = "Ask Qwen a short question…"
            setHintTextColor(0xFF9CA3AF.toInt())
            setTextColor(0xFFF9FAFB.toInt())
            textSize = 15f
            minLines = 2
            maxLines = 4
            setPadding(dp(12), dp(10), dp(12), dp(10))
            setBackgroundColor(0xFF20232B.toInt())
        }
        content.addView(inferencePrompt)
        inferenceButton = Button(this).apply {
            text = "Run local Qwen test"
            isEnabled = false
            setOnClickListener { runLocalInference() }
        }
        content.addView(inferenceButton)
        inferenceOutput = TextView(this).apply {
            textSize = 14f
            setTextColor(0xFFE5E7EB.toInt())
            setPadding(0, dp(12), 0, dp(8))
        }
        content.addView(inferenceOutput)
        addCard("DEVICE MEMORY", "Inference uses substantial RAM", "Loading a multi-gigabyte model and its context needs free memory. Close other heavy apps first; Android may still stop inference if memory is insufficient.")
        addCard("PRIVACY", "Stored privately on this device", "The selected model is copied into Zexa's app-private storage. No model file is uploaded to a server.")
        refreshModelStatus()
    }

    private fun openModelPicker() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            startActivityForResult(intent, modelPickerRequest)
        } catch (_: Exception) {
            Toast.makeText(this, "No file picker is available on this device.", Toast.LENGTH_LONG).show()
        }
    }

    @Deprecated("Uses the platform document picker for compatibility with the current Activity foundation.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != modelPickerRequest || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        importSelectedModel(uri)
    }

    private fun importSelectedModel(uri: Uri) {
        modelImportButton?.isEnabled = false
        inferenceButton?.isEnabled = false
        modelImportButton?.text = "Validating and importing…"
        brainStatus?.text = "Import in progress. Keep Zexa open until it finishes."
        Thread {
            try {
                if (nativeModelLoaded) {
                    NativeQwenRuntime.nativeUnloadModel()
                    nativeModelLoaded = false
                }
                val expectedSize = queryModelSize(uri)
                val stream = contentResolver.openInputStream(uri)
                    ?: throw IllegalStateException("Could not open the selected model file.")
                val imported = modelStore.importModel(stream, expectedSize)
                getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE).edit()
                    .putLong("model_size_bytes", imported.sizeBytes)
                    .putString("model_sha256", imported.sha256)
                    .apply()
                runOnUiThread {
                    modelImportButton?.isEnabled = true
                    modelImportButton?.text = "Replace Qwen GGUF model"
                    refreshModelStatus()
                    Toast.makeText(this, "GGUF model imported and verified.", Toast.LENGTH_LONG).show()
                }
            } catch (error: Exception) {
                runOnUiThread {
                    modelImportButton?.isEnabled = true
                    modelImportButton?.text = "Try model import again"
                    refreshModelStatus()
                    brainStatus?.text = "Import failed: " + (error.message ?: "unknown error")
                    Toast.makeText(this, "Model import failed. Check storage and file format.", Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }


    private fun loadLocalModel() {
        val model = modelStore.installedModel()
        if (model == null) {
            Toast.makeText(this, "Import a valid GGUF model first.", Toast.LENGTH_LONG).show()
            return
        }
        modelLoadButton?.isEnabled = false
        modelLoadButton?.text = "Loading model…"
        inferenceOutput?.text = "Loading Qwen into native memory. This can take time and use substantial RAM."
        Thread {
            try {
                val expectedHash = getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE)
                    .getString("model_sha256", null)
                if (!modelStore.verifyInstalledModel(expectedHash)) {
                    throw IllegalStateException("Stored model integrity check failed. Import the GGUF again.")
                }
                NativeQwenRuntime.nativeLoadModel(model.absolutePath, 2048, 4)
                nativeModelLoaded = true
                runOnUiThread {
                    modelLoadButton?.isEnabled = true
                    modelLoadButton?.text = "Qwen loaded — reload model"
                    inferenceButton?.isEnabled = true
                    inferenceOutput?.text = "Qwen runtime loaded. Send a short test prompt below."
                }
            } catch (error: UnsatisfiedLinkError) {
                runOnUiThread {
                    modelLoadButton?.isEnabled = true
                    modelLoadButton?.text = "Load model into memory"
                    inferenceOutput?.text = "Native runtime is unavailable in this APK: " + (error.message ?: "library load failed")
                }
            } catch (error: Exception) {
                runOnUiThread {
                    modelLoadButton?.isEnabled = true
                    modelLoadButton?.text = "Retry model load"
                    inferenceOutput?.text = "Model load failed: " + (error.message ?: "unknown error")
                }
            }
        }.start()
    }

    private fun runLocalInference() {
        val prompt = inferencePrompt?.text?.toString()?.trim().orEmpty()
        if (!nativeModelLoaded) {
            Toast.makeText(this, "Load the Qwen model first.", Toast.LENGTH_LONG).show()
            return
        }
        if (prompt.isEmpty()) {
            Toast.makeText(this, "Enter a question first.", Toast.LENGTH_LONG).show()
            return
        }
        inferenceButton?.isEnabled = false
        inferenceOutput?.text = "Generating local response…"
        Thread {
            try {
                val answer = NativeQwenRuntime.nativeGenerate(
                    "You are Zexa, a helpful assistant. Reply clearly in the user's language, including Hindi or Hinglish when appropriate.",
                    prompt,
                    256,
                )
                runOnUiThread {
                    inferenceButton?.isEnabled = nativeModelLoaded
                    inferenceOutput?.text = if (answer.isBlank()) "The model returned an empty response." else answer
                }
            } catch (error: UnsatisfiedLinkError) {
                runOnUiThread {
                    inferenceButton?.isEnabled = false
                    inferenceOutput?.text = "Native runtime is unavailable: " + (error.message ?: "library load failed")
                }
            } catch (error: Exception) {
                runOnUiThread {
                    inferenceButton?.isEnabled = nativeModelLoaded
                    inferenceOutput?.text = "Inference failed: " + (error.message ?: "unknown error")
                }
            }
        }.start()
    }

    private fun queryModelSize(uri: Uri): Long? {
        var cursor: Cursor? = null
        return try {
            cursor = contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)
            if (cursor != null && cursor.moveToFirst()) {
                val index = cursor.getColumnIndex(OpenableColumns.SIZE)
                if (index >= 0 && !cursor.isNull(index)) cursor.getLong(index) else null
            } else null
        } catch (_: Exception) {
            null
        } finally {
            cursor?.close()
        }
    }

    private fun refreshModelStatus() {
        val status = brainStatus ?: return
        val model = modelStore.installedModel()
        if (model == null) {
            status.text = "No GGUF model imported yet. Select a compatible GGUF file to copy it into private app storage."
            modelLoadButton?.isEnabled = false
            inferenceButton?.isEnabled = false
            return
        }
        val size = model.length() / (1024.0 * 1024.0 * 1024.0)
        val hash = getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE)
            .getString("model_sha256", null)
        status.text = "Model imported: " + String.format("%.2f", size) + " GiB\nSHA-256: " +
            (hash ?: "not recorded") + "\nInference status: not connected (native llama.cpp runtime pending)."
        modelImportButton?.text = "Replace Qwen GGUF model"
        modelLoadButton?.isEnabled = !nativeModelLoaded
        if (nativeModelLoaded) {
            modelLoadButton?.text = "Qwen loaded — reload model"
            inferenceButton?.isEnabled = true
        } else {
            modelLoadButton?.text = "Load model into memory"
            inferenceButton?.isEnabled = false
        }
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
