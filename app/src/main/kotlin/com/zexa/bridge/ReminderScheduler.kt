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

object ReminderScheduler {
    const val TAG = "zexa-user-reminder"
    const val MAX_DELAY_MINUTES = 10080L

    fun schedule(context: Context, title: String, message: String, delayMinutes: Long): UUID {
        require(title.isNotBlank() && title.length <= ReminderWorker.MAX_TITLE_LENGTH)
        require(message.isNotBlank() && message.length <= ReminderWorker.MAX_MESSAGE_LENGTH)
        require(delayMinutes in 1L..MAX_DELAY_MINUTES)

        val request = OneTimeWorkRequest.Builder(ReminderWorker::class.java)
            .setInitialDelay(delayMinutes, TimeUnit.MINUTES)
            .setInputData(
                Data.Builder()
                    .putString(ReminderWorker.KEY_TITLE, title)
                    .putString(ReminderWorker.KEY_MESSAGE, message)
                    .build()
            )
            .addTag(TAG)
            .build()
        WorkManager.getInstance(context.applicationContext).enqueueUniqueWork(
            "zexa-reminder-${request.id}",
            ExistingWorkPolicy.KEEP,
            request
        )
        return request.id
    }

    fun cancelAll(context: Context) {
        WorkManager.getInstance(context.applicationContext).cancelAllWorkByTag(TAG)
    }

    fun pendingSummary(context: Context): String {
        val infos = WorkManager.getInstance(context.applicationContext).getWorkInfosByTag(TAG).get()
        val active = infos.count { !it.state.isFinished }
        val running = infos.count { it.state == androidx.work.WorkInfo.State.RUNNING }
        return "$active active reminder job(s); $running currently running."
    }
}
