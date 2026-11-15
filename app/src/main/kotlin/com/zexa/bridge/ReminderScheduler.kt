package com.zexa.bridge

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequest
import androidx.work.Operation
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.UUID
import java.util.concurrent.TimeUnit

class ReminderWorker(context: Context, parameters: WorkerParameters) : Worker(context, parameters) {
    override fun doWork(): Result {
        val title = inputData.getString(KEY_TITLE)?.take(MAX_TITLE_LENGTH)?.takeIf { it.isNotBlank() }
            ?: return Result.failure()
        val message = inputData.getString(KEY_MESSAGE)?.take(MAX_MESSAGE_LENGTH)?.takeIf { it.isNotBlank() }
            ?: return Result.failure()
        if (Build.VERSION.SDK_INT >= 33 &&
            applicationContext.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            return Result.failure()
        }
        if (!NotificationManagerCompat.from(applicationContext).areNotificationsEnabled()) {
            return Result.failure()
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Zexa reminders",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "User-created local reminders"
            }
            manager.createNotificationChannel(channel)
        }

        val openApp = PendingIntent.getActivity(
            applicationContext,
            id.toString().hashCode(),
            Intent(applicationContext, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setContentIntent(openApp)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()
        return try {
            NotificationManagerCompat.from(applicationContext).notify(
                (id.toString().hashCode() and 0x7fffffff),
                notification
            )
            Result.success()
        } catch (_: SecurityException) {
            // Notification permission may be revoked after scheduling.
            Result.failure()
        }
    }

    companion object {
        const val KEY_TITLE = "title"
        const val KEY_MESSAGE = "message"
        const val CHANNEL_ID = "zexa_reminders"
        const val MAX_TITLE_LENGTH = 80
        const val MAX_MESSAGE_LENGTH = 500
    }
}

object ReminderRules {
    fun isValid(title: String, message: String, delayMinutes: Long): Boolean =
        title.isNotBlank() &&
            title.length <= ReminderWorker.MAX_TITLE_LENGTH &&
            message.isNotBlank() &&
            message.length <= ReminderWorker.MAX_MESSAGE_LENGTH &&
            delayMinutes in 1L..ReminderScheduler.MAX_DELAY_MINUTES
}

data class ScheduledReminder(val id: UUID, val operation: Operation)

data class PendingReminderInfo(
    val id: UUID,
    val state: androidx.work.WorkInfo.State,
    val title: String,
    val message: String
)

object ReminderScheduler {
    const val TAG = "zexa-user-reminder"
    private const val TITLE_TAG = "zexa-reminder-title:"
    private const val MESSAGE_TAG = "zexa-reminder-message:"
    const val MAX_DELAY_MINUTES = 10080L

    fun schedule(context: Context, title: String, message: String, delayMinutes: Long): ScheduledReminder {
        require(ReminderRules.isValid(title, message, delayMinutes)) {
            "Reminder title, message or delay is invalid."
        }

        val request = OneTimeWorkRequest.Builder(ReminderWorker::class.java)
            .setInitialDelay(delayMinutes, TimeUnit.MINUTES)
            .setInputData(
                Data.Builder()
                    .putString(ReminderWorker.KEY_TITLE, title)
                    .putString(ReminderWorker.KEY_MESSAGE, message)
                    .build()
            )
            .addTag(TAG)
            .addTag(TITLE_TAG + title)
            .addTag(MESSAGE_TAG + message)
            .build()
        val operation = WorkManager.getInstance(context.applicationContext).enqueueUniqueWork(
            "zexa-reminder-${request.id}",
            ExistingWorkPolicy.KEEP,
            request
        )
        return ScheduledReminder(request.id, operation)
    }

    fun cancelAll(context: Context): Operation =
        WorkManager.getInstance(context.applicationContext).cancelAllWorkByTag(TAG)

    fun pending(context: Context): List<PendingReminderInfo> =
        WorkManager.getInstance(context.applicationContext).getWorkInfosByTag(TAG).get()
            .filter { !it.state.isFinished }
            .map { info ->
                PendingReminderInfo(
                    id = info.id,
                    state = info.state,
                    title = info.tags.firstOrNull { it.startsWith(TITLE_TAG) }
                        ?.removePrefix(TITLE_TAG)?.take(ReminderWorker.MAX_TITLE_LENGTH)
                        ?.takeIf { it.isNotBlank() } ?: "Reminder",
                    message = info.tags.firstOrNull { it.startsWith(MESSAGE_TAG) }
                        ?.removePrefix(MESSAGE_TAG)?.take(ReminderWorker.MAX_MESSAGE_LENGTH).orEmpty()
                )
            }

    fun cancel(context: Context, id: UUID): Operation =
        WorkManager.getInstance(context.applicationContext).cancelWorkById(id)

    fun pendingSummary(context: Context): String {
        val infos = pending(context)
        val running = infos.count { it.state == androidx.work.WorkInfo.State.RUNNING }
        return "${infos.size} active reminder job(s); $running currently running."
    }
}
