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
            setProgressAsync(workDataOf("stage" to "checking")).get()

            val modelStore = LocalModelStore(File(applicationContext.filesDir, "models"))
            val model = modelStore.installedModel()
                ?: throw IllegalStateException("No valid GGUF model is installed. Import a model first.")
            ModelLoadCoordinator.publish(applicationContext, "loading", "Verifying and loading Qwen into native memory. This may take several minutes.")
            setProgressAsync(workDataOf("stage" to "loading")).get()
            NativeQwenSession.loadVerified(model, {
                val expectedHash = applicationContext.getSharedPreferences("zexa_bridge", Context.MODE_PRIVATE)
                    .getString("model_sha256", null)
                modelStore.verifyInstalledModel(expectedHash)
            }, 2048, 4)

            setProgressAsync(workDataOf("stage" to "complete")).get()
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
        ModelLoadCoordinator.publishInterruptedIfActive(
            applicationContext,
            "Loading was interrupted. Tap Retry to start it again."
        )
        super.onStopped()
    }
}
