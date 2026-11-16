package com.zexa.bridge

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * Explicit, user-started voice I/O. Recognition is restricted to Android's on-device
 * recognizer; this class does not fall back to a network recognition service.
 */
class OnDeviceVoiceController(
    private val activity: Activity,
    private val onStatus: (String) -> Unit,
    private val onRecognized: (String) -> Unit,
) {
    private var recognizer: SpeechRecognizer? = null
    private var textToSpeech: TextToSpeech? = null
    private var ttsReady = false
    private var pendingSpeech: String? = null

    fun startListening() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            onStatus("On-device speech recognition requires Android 12 or newer.")
            return
        }
        if (!SpeechRecognizer.isOnDeviceRecognitionAvailable(activity)) {
            onStatus("No on-device speech recognition service is available. Install an offline language pack or use text chat.")
            return
        }
        try {
            if (recognizer == null) {
                recognizer = SpeechRecognizer.createOnDeviceSpeechRecognizer(activity).also { speech ->
                    speech.setRecognitionListener(object : RecognitionListener {
                        override fun onReadyForSpeech(params: Bundle?) {
                            onStatus("Listening on this device…")
                        }

                        override fun onBeginningOfSpeech() {
                            onStatus("Speech detected…")
                        }

                        override fun onRmsChanged(rmsdB: Float) = Unit
                        override fun onBufferReceived(buffer: ByteArray?) = Unit

                        override fun onEndOfSpeech() {
                            onStatus("Recognizing speech…")
                        }

                        override fun onError(error: Int) {
                            onStatus("Voice input stopped (recognizer error $error). You can try again.")
                        }

                        override fun onResults(results: Bundle?) {
                            val text = results
                                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                                ?.firstOrNull()
                                ?.trim()
                                .orEmpty()
                            if (text.isEmpty()) {
                                onStatus("No speech was recognized. Try again or type your message.")
                            } else {
                                onStatus("Voice input ready. Review the recognized text before sending.")
                                onRecognized(text)
                            }
                        }

                        override fun onPartialResults(partialResults: Bundle?) = Unit
                        override fun onEvent(eventType: Int, params: Bundle?) = Unit
                    })
                }
            }
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
                putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            }
            onStatus("Starting on-device voice input…")
            recognizer?.startListening(intent)
        } catch (error: Exception) {
            onStatus("Could not start on-device voice input: " + (error.message ?: "unknown error"))
        }
    }

    fun stopListening() {
        try {
            recognizer?.cancel()
        } catch (_: Exception) {
            // Cancellation is best-effort during navigation or Activity shutdown.
        }
    }

    fun speak(text: String) {
        val safeText = text.trim().take(4000)
        if (safeText.isEmpty()) {
            onStatus("There is no assistant response to read aloud yet.")
            return
        }
        pendingSpeech = safeText
        if (textToSpeech == null) {
            onStatus("Preparing the installed text-to-speech engine…")
            textToSpeech = TextToSpeech(activity) { result ->
                if (result == TextToSpeech.SUCCESS) {
                    val engine = textToSpeech
                    val languageResult = engine?.setLanguage(Locale.forLanguageTag("hi-IN"))
                    ttsReady = languageResult != null &&
                        languageResult != TextToSpeech.LANG_MISSING_DATA &&
                        languageResult != TextToSpeech.LANG_NOT_SUPPORTED
                    if (ttsReady) {
                        val queued = pendingSpeech
                        pendingSpeech = null
                        if (queued != null) {
                            onStatus("Speaking with the installed Hindi voice.")
                            engine?.speak(queued, TextToSpeech.QUEUE_FLUSH, null, "zexa-answer")
                        }
                    } else {
                        pendingSpeech = null
                        onStatus("Hindi voice is unavailable in the installed TTS engine. Install a Hindi voice or use text chat.")
                    }
                } else {
                    pendingSpeech = null
                    onStatus("Text-to-speech engine initialization failed.")
                }
            }
            return
        }
        if (!ttsReady) {
            onStatus("The installed Hindi text-to-speech voice is still preparing or unavailable.")
            return
        }
        val queued = pendingSpeech
        pendingSpeech = null
        if (queued != null) {
            onStatus("Speaking with the installed Hindi voice.")
            textToSpeech?.speak(queued, TextToSpeech.QUEUE_FLUSH, null, "zexa-answer")
        }
    }

    fun stopSpeaking() {
        pendingSpeech = null
        textToSpeech?.stop()
    }

    fun shutdown() {
        stopListening()
        recognizer?.destroy()
        recognizer = null
        textToSpeech?.stop()
        textToSpeech?.shutdown()
        textToSpeech = null
        ttsReady = false
        pendingSpeech = null
    }
}
