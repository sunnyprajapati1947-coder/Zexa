package com.zexa.bridge

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import java.io.File

/**
 * Persisted WorkManager entry point for loading the local GGUF into the
 * process-scoped llama.cpp runtime. A killed process releases native memory;
 * WorkManager can rerun the request and the installed file is re-verified.
 */
class QwenModelLoadWorker(
    appContext: Context,
    params: WorkerParameters,
) : Worker(appContext, params) {
    override fun doWork(): Result {
        return try {
            if (ChatGenerationGate.isRunning) {
                ModelLoadCoordinator.publish(applicationContext, "waiting", "Waiting for the current response to finish.")
                return Result.retry()
            }

            ModelLoadCoordinator.publish(applicationContext, "checking", "Checking the installed GGUF integrity…")
            setProgressAsync(workDataOf("stage" to "checking", "percent" to 10)).get()

            val modelStore = LocalModelStore(File(applicationContext.filesDir, "models"))
            val model = modelStore.installedModel()
                ?: throw IllegalStateException("No valid GGUF model is installed. Import a model first.")
            val expectedHash = applicationContext.getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE)
                .getString("model_sha256", null)
            if (!modelStore.verifyInstalledModel(expectedHash)) {
                throw IllegalStateException("Stored model integrity check failed. Import the GGUF again.")
            }

            ModelLoadCoordinator.publish(applicationContext, "loading", "Loading Qwen into native memory. This may take several minutes.")
            setProgressAsync(workDataOf("stage" to "loading", "percent" to 25)).get()
            NativeQwenSession.load(model, 2048, 4)

            setProgressAsync(workDataOf("stage" to "complete", "percent" to 100)).get()
            ModelLoadCoordinator.publish(applicationContext, "loaded", "Qwen is loaded and ready for local inference.")
            Result.success()
        } catch (error: UnsatisfiedLinkError) {
            val detail = "Native runtime unavailable: " + (error.message ?: "library load failed")
            ModelLoadCoordinator.publish(applicationContext, "failed", detail)
            Result.failure(workDataOf("error" to detail))
        } catch (error: Exception) {
            val detail = error.message ?: "Unknown model loading error."
            ModelLoadCoordinator.publish(applicationContext, "failed", detail)
            Result.failure(workDataOf("error" to detail))
        }
    }

    override fun onStopped() {
        ModelLoadCoordinator.publish(applicationContext, "interrupted", "Loading was interrupted. Tap Retry to start it again.")
        super.onStopped()
    }
}
