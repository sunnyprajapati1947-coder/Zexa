package com.zexa.bridge

import android.app.Activity
import android.app.AlertDialog
import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.pm.PackageManager
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
    private var chatLog: LinearLayout? = null
    private var chatInput: EditText? = null
    private var chatSendButton: Button? = null
    private var chatScroll: ScrollView? = null
    private val chatHistory = ArrayList<Pair<String, String>>()
    private val chatStore by lazy { ChatHistoryStore(this) }
    private var voiceController: OnDeviceVoiceController? = null
    private var voiceStatus: TextView? = null
    private val voicePermissionRequest = 4208
    private val notificationPermissionRequest = 4209
    private var pendingReminder: Triple<String, String, Long>? = null
    private var reminderStatus: TextView? = null
    @Volatile private var chatGenerating = false
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
        chatHistory.addAll(chatStore.loadRecent())
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
        if (section != "Chat") voiceController?.stopListening()
        when (section) {
            "Home" -> showHome()
            "Chat" -> showChat()
            "Brain" -> showBrain()
            "Tasks" -> showTasks()
            "Memory" -> showMemory()
            "Device" -> showDevice()
        }
    }

    private fun showHome() {
        content.removeAllViews()
        addHeading("Your assistant, in progress")
        addCard("APP STATUS", "Native assistant foundation active", "Local Qwen chat, saved chat history, user-started voice controls and basic local reminders are implemented on this branch. Device validation and several advanced modules remain.")
        addCard("AI BRAIN", "Native Qwen integration under validation", "GGUF import and llama.cpp JNI inference code are in place; CI and real-device inference still need verification.")
        addCard("VOICE", "On-device voice controls added", "Chat offers explicit microphone input using Android's on-device recognizer and optional spoken replies using the installed Hindi TTS voice. Device language packs may be required.")
        addCard("CHAT HISTORY", "Saved privately on this device", "The latest completed local chat messages are stored in Zexa's app-private database.")
        addCard("REMINDERS", "Available in Tasks", "Create local WorkManager reminders with notification permission. Delivery is best-effort and may be delayed by Android battery controls.")
        addCard("DEVICE HAND", "Optional and OFF by default", "Accessibility access is separate from AI chat and remains user-controlled.")
        addButton("Open device settings") { showDevice() }
    }



    private fun showChat() {
        content.removeAllViews()
        addHeading("Zexa chat")
        if (!nativeModelLoaded) {
            addCard("LOCAL BRAIN", "Qwen is not loaded", "Open Brain, import a compatible GGUF model and load it before chatting.")
            addButton("Open Brain") { showBrain() }
        } else {
            addCard("LOCAL BRAIN", "Qwen ready in this app session", "Messages are processed on-device by the loaded local model.")
        }
        chatScroll = ScrollView(this).apply {
            isFillViewport = true
            setBackgroundColor(0xFF17191F.toInt())
        }
        chatLog = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(10), dp(10), dp(10), dp(10))
        }
        chatScroll?.addView(chatLog, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        content.addView(chatScroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(300)))
        renderChatHistory()
        chatInput = EditText(this).apply {
            hint = "Message Zexa…"
            setHintTextColor(0xFF9CA3AF.toInt())
            setTextColor(0xFFF9FAFB.toInt())
            textSize = 15f
            minLines = 2
            maxLines = 4
            setPadding(dp(12), dp(10), dp(12), dp(10))
            setBackgroundColor(0xFF20232B.toInt())
        }
        content.addView(chatInput)
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        chatSendButton = Button(this).apply {
            text = "Send"
            isEnabled = nativeModelLoaded && !chatGenerating
            setOnClickListener { sendChatMessage() }
        }
        actions.addView(chatSendButton, LinearLayout.LayoutParams(0, dp(48), 1f))
        actions.addView(Button(this).apply {
            text = "New chat"
            setOnClickListener {
                if (chatGenerating) {
                    Toast.makeText(this@MainActivity, "Wait for the current response to finish.", Toast.LENGTH_SHORT).show()
                } else {
                    chatHistory.clear()
                    chatStore.clear()
                    renderChatHistory()
                }
            }
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        content.addView(actions)
        val voiceActions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        voiceActions.addView(Button(this).apply {
            text = "On-device voice input"
            setOnClickListener { requestVoiceInput() }
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        voiceActions.addView(Button(this).apply {
            text = "Speak latest reply"
            setOnClickListener {
                val latest = chatHistory.lastOrNull { it.first == "assistant" }?.second
                if (latest == null) {
                    voiceStatus?.text = "No assistant response is available to read aloud."
                } else {
                    ensureVoiceController().speak(latest)
                }
            }
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        content.addView(voiceActions)
        content.addView(Button(this).apply {
            text = "Stop voice input / audio"
            setOnClickListener {
                voiceController?.stopListening()
                voiceController?.stopSpeaking()
                voiceStatus?.text = "Voice activity stopped."
            }
        })
        voiceStatus = TextView(this).apply {
            text = "Voice is off. Tap the microphone button to start; recognized text will be placed in the message box for your review."
            textSize = 12f
            setTextColor(0xFFD1D5DB.toInt())
            setPadding(dp(4), dp(8), dp(4), dp(10))
        }
        content.addView(voiceStatus)
        addCard("VOICE PRIVACY", "Microphone is user-started", "Recognition uses Android's on-device speech recognizer only; Zexa does not fall back to a network recognizer. Spoken output uses the installed Android TTS engine, whose voice data and privacy behavior are controlled by that engine.")
        addCard("LOCAL HISTORY", "Saved on this device", "The latest completed conversation is stored in Zexa's private app database. Open Memory to clear it.")
    }

    private fun requestVoiceInput() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), voicePermissionRequest)
            return
        }
        startOnDeviceVoiceInput()
    }

    private fun startOnDeviceVoiceInput() {
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.S) {
            voiceStatus?.text = "On-device speech recognition requires Android 12 or newer."
            return
        }
        ensureVoiceController().startListening()
    }

    private fun ensureVoiceController(): OnDeviceVoiceController {
        val existing = voiceController
        if (existing != null) return existing
        return OnDeviceVoiceController(
            this,
            onStatus = { message -> runOnUiThread { voiceStatus?.text = message } },
            onRecognized = { recognized ->
                runOnUiThread {
                    chatInput?.setText(recognized)
                    chatInput?.setSelection(recognized.length)
                    voiceStatus?.text = "Recognized text inserted. Review it, then tap Send when ready."
                }
            },
        ).also { voiceController = it }
    }

    @Deprecated("Uses the Activity permission callback for compatibility with the current app foundation.")
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == voicePermissionRequest) {
            if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
                startOnDeviceVoiceInput()
            } else {
                voiceStatus?.text = "Microphone permission was not granted. You can continue using text chat."
            }
            return
        }
        if (requestCode == notificationPermissionRequest) {
            if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
                schedulePendingReminder()
            } else {
                pendingReminder = null
                reminderStatus?.text = "Notification permission was not granted. Reminder was not scheduled."
            }
        }
    }

    private fun sendChatMessage() {
        if (chatGenerating) return
        if (!nativeModelLoaded) {
            Toast.makeText(this, "Load Qwen from Brain first.", Toast.LENGTH_LONG).show()
            return
        }
        val message = chatInput?.text?.toString()?.trim().orEmpty()
        if (message.isEmpty()) return
        chatHistory.add("user" to message)
        while (chatHistory.size > 15) {
            if (chatHistory.size >= 3) {
                chatHistory.removeAt(0)
                chatHistory.removeAt(0)
            } else break
        }
        chatInput?.setText("")
        chatGenerating = true
        chatSendButton?.isEnabled = false
        renderChatHistory()
        val conversation = chatHistory.toList()
        Thread {
            try {
                val answer = NativeQwenRuntime.nativeGenerate(
                    "You are Zexa, a helpful assistant. Reply in the user's language, including Hindi or Hinglish when appropriate.",
                    conversation.map { it.first }.toTypedArray(),
                    conversation.map { it.second }.toTypedArray(),
                    256,
                )
                val persistenceError = try {
                    chatStore.saveCompletedConversation(conversation + ("assistant" to answer))
                    null
                } catch (storageError: Exception) {
                    storageError.message ?: "database write failed"
                }
                runOnUiThread {
                    chatHistory.add("assistant" to answer)
                    chatGenerating = false
                    chatSendButton?.isEnabled = nativeModelLoaded
                    renderChatHistory()
                    if (persistenceError != null) addChatNotice("Chat is active, but local history could not be saved: $persistenceError")
                }
            } catch (error: UnsatisfiedLinkError) {
                runOnUiThread {
                    if (chatHistory.lastOrNull()?.first == "user") chatHistory.removeAt(chatHistory.lastIndex)
                    chatGenerating = false
                    chatSendButton?.isEnabled = false
                    renderChatHistory()
                    addChatNotice("Native runtime unavailable: " + (error.message ?: "library load failed"))
                }
            } catch (error: Exception) {
                runOnUiThread {
                    if (chatHistory.lastOrNull()?.first == "user") chatHistory.removeAt(chatHistory.lastIndex)
                    chatGenerating = false
                    chatSendButton?.isEnabled = nativeModelLoaded
                    renderChatHistory()
                    addChatNotice("Local response failed: " + (error.message ?: "unknown error"))
                }
            }
        }.start()
    }

    private fun renderChatHistory() {
        val log = chatLog ?: return
        log.removeAllViews()
        if (chatHistory.isEmpty()) {
            log.addView(TextView(this).apply {
                text = "Your local conversation will appear here."
                textSize = 14f
                setTextColor(0xFF9CA3AF.toInt())
                setPadding(dp(8), dp(18), dp(8), dp(18))
            })
        }
        chatHistory.forEach { item ->
            val role = item.first
            val message = item.second
            val bubble = TextView(this).apply {
                text = (if (role == "user") "YOU" else "ZEXA") + "\n" + message
                textSize = 14f
                setTextColor(0xFFF9FAFB.toInt())
                setTextIsSelectable(true)
                setPadding(dp(12), dp(10), dp(12), dp(10))
                setBackgroundColor(if (role == "user") 0xFF303744.toInt() else 0xFF20232B.toInt())
            }
            val params = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            params.bottomMargin = dp(8)
            log.addView(bubble, params)
        }
        chatScroll?.post { chatScroll?.fullScroll(View.FOCUS_DOWN) }
    }

    private fun addChatNotice(message: String) {
        val log = chatLog ?: return
        log.addView(TextView(this).apply {
            text = message
            textSize = 12f
            setTextColor(0xFFFFC4A8.toInt())
            setPadding(dp(8), dp(8), dp(8), dp(8))
        })
        chatScroll?.post { chatScroll?.fullScroll(View.FOCUS_DOWN) }
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
        if (chatGenerating) {
            Toast.makeText(this, "Wait for the current chat response before replacing the model.", Toast.LENGTH_LONG).show()
            return
        }
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
        if (chatGenerating) {
            Toast.makeText(this, "Wait for the current chat response before reloading the model.", Toast.LENGTH_LONG).show()
            return
        }
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
                // Activity recreation can reset this Activity's flag while the process-level
                // JNI model remains loaded. Release it before loading again to avoid doubling RAM.
                NativeQwenRuntime.nativeUnloadModel()
                NativeQwenRuntime.nativeLoadModel(model.absolutePath, 2048, 4)
                nativeModelLoaded = true
                runOnUiThread {
                    modelLoadButton?.isEnabled = false
                    modelLoadButton?.text = "Qwen loaded"
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
                    arrayOf("user"),
                    arrayOf(prompt),
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
                if (index >= 0 && !cursor.isNull(index)) cursor.getLong(index).takeIf { it > 0L } else null
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
            (hash ?: "not recorded") + "\nInference status: " +
            if (nativeModelLoaded) "Qwen is loaded in this app process." else "Model is imported; load it to start local inference."
        modelImportButton?.text = "Replace Qwen GGUF model"
        modelLoadButton?.isEnabled = !nativeModelLoaded
        if (nativeModelLoaded) {
            modelLoadButton?.text = "Qwen loaded"
            inferenceButton?.isEnabled = true
        } else {
            modelLoadButton?.text = "Load model into memory"
            inferenceButton?.isEnabled = false
        }
    }

    private fun showMemory() {
        content.removeAllViews()
        addHeading("Private memory")
        val savedCount = chatStore.loadRecent(ChatHistoryStore.MAX_HISTORY_LIMIT).size
        addCard(
            "LOCAL CHAT HISTORY",
            "$savedCount messages saved",
            "Only completed local conversations are stored in Zexa's app-private database. They are not uploaded or synced."
        )
        addButton("Clear saved chat history") {
            if (chatGenerating) {
                Toast.makeText(this, "Wait for the current response to finish.", Toast.LENGTH_LONG).show()
            } else {
                AlertDialog.Builder(this)
                    .setTitle("Clear local chat history?")
                    .setMessage("This permanently deletes the saved conversations from this app on this device.")
                    .setNegativeButton("Cancel", null)
                    .setPositiveButton("Clear") { _, _ ->
                        chatStore.clear()
                        chatHistory.clear()
                        showMemory()
                        Toast.makeText(this, "Local chat history cleared.", Toast.LENGTH_SHORT).show()
                    }
                    .show()
            }
        }
        addCard(
            "MEMORY STATUS",
            "Conversation history only",
            "Automatic personal-memory extraction, semantic search, and editable memory facts are not implemented yet."
        )
        addCard(
            "TASKS & REMINDERS",
            "Basic local reminders available",
            "WorkManager scheduling and notifications are wired in. Full task management, editing and target-device background validation remain pending."
        )
    }

    private fun showTasks() {
        content.removeAllViews()
        addHeading("Tasks & reminders")
        addCard(
            "ANDROID BACKGROUND WORK",
            "Persistent local reminders",
            "Reminders are stored by Android WorkManager and can run after Zexa is closed or the device restarts. Delivery is best-effort and may be delayed by Doze, battery controls or system scheduling."
        )
        val titleInput = EditText(this).apply {
            hint = "Reminder title"
            setSingleLine(true)
            setTextColor(0xFFF9FAFB.toInt())
            setHintTextColor(0xFF9CA3AF.toInt())
        }
        content.addView(titleInput)
        val messageInput = EditText(this).apply {
            hint = "What should Zexa remind you about?"
            minLines = 2
            maxLines = 4
            setTextColor(0xFFF9FAFB.toInt())
            setHintTextColor(0xFF9CA3AF.toInt())
        }
        content.addView(messageInput)
        val delayInput = EditText(this).apply {
            hint = "Minutes from now (1–10080)"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            setSingleLine(true)
            setTextColor(0xFFF9FAFB.toInt())
            setHintTextColor(0xFF9CA3AF.toInt())
        }
        content.addView(delayInput)
        val statusView = TextView(this).apply {
            textSize = 13f
            setTextColor(0xFFD1D5DB.toInt())
            setPadding(0, dp(10), 0, dp(10))
        }
        reminderStatus = statusView
        content.addView(statusView)
        content.addView(Button(this).apply {
            text = "Schedule reminder"
            setOnClickListener {
                val title = titleInput.text.toString().trim()
                val message = messageInput.text.toString().trim()
                val delay = delayInput.text.toString().trim().toLongOrNull()
                if (title.isEmpty() || message.isEmpty() || delay == null || delay !in 1L..ReminderScheduler.MAX_DELAY_MINUTES) {
                    reminderStatus?.text = "Enter a title, message and a delay between 1 and 10080 minutes."
                    return@setOnClickListener
                }
                pendingReminder = Triple(title, message, delay)
                if (android.os.Build.VERSION.SDK_INT >= 33 &&
                    checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
                ) {
                    requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), notificationPermissionRequest)
                } else {
                    schedulePendingReminder()
                }
            }
        })
        content.addView(Button(this).apply {
            text = "Cancel all pending reminders"
            setOnClickListener {
                AlertDialog.Builder(this@MainActivity)
                    .setTitle("Cancel all reminders?")
                    .setMessage("This cancels all pending Zexa reminders on this device.")
                    .setNegativeButton("Keep reminders", null)
                    .setPositiveButton("Cancel reminders") { _, _ ->
                        reminderStatus?.text = "Cancelling pending reminders…"
                        Thread {
                            try {
                                ReminderScheduler.cancelAll(this@MainActivity).result.get()
                                runOnUiThread { reminderStatus?.text = "All pending Zexa reminders were cancelled." }
                            } catch (error: Exception) {
                                runOnUiThread {
                                    reminderStatus?.text = "Could not cancel reminders: " + (error.message ?: "unknown error")
                                }
                            }
                        }.start()
                    }
                    .show()
            }
        })
        Thread {
            try {
                val summary = ReminderScheduler.pendingSummary(this)
                runOnUiThread { reminderStatus?.text = summary }
            } catch (error: Exception) {
                runOnUiThread { reminderStatus?.text = "Could not read reminder status: " + (error.message ?: "unknown error") }
            }
        }.start()
    }

    private fun schedulePendingReminder() {
        val reminder = pendingReminder ?: return
        pendingReminder = null
        reminderStatus?.text = "Saving reminder…"
        Thread {
            try {
                val scheduled = ReminderScheduler.schedule(this, reminder.first, reminder.second, reminder.third)
                scheduled.operation.result.get()
                runOnUiThread {
                    reminderStatus?.text = "Reminder scheduled for about ${reminder.third} minute(s) from now. ID: ${scheduled.id}"
                    Toast.makeText(this, "Local reminder scheduled.", Toast.LENGTH_LONG).show()
                }
            } catch (error: Exception) {
                runOnUiThread {
                    reminderStatus?.text = "Could not schedule reminder: " + (error.message ?: "unknown error")
                }
            }
        }.start()
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

    override fun onPause() {
        voiceController?.stopListening()
        voiceController?.stopSpeaking()
        super.onPause()
    }

    override fun onDestroy() {
        voiceController?.shutdown()
        voiceController = null
        super.onDestroy()
    }

    override fun onResume() {
        super.onResume()
        ZexaAccessibilityService.instance?.refreshBridge()
        if (::bridgeButton.isInitialized) refreshBridgeUi()
    }
}
