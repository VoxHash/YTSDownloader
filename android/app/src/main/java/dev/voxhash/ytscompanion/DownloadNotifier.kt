package dev.voxhash.ytscompanion

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat

/**
 * Slice 7: local download progress / done / error notifications (no FCM / Play Services).
 * Channel created on first use; posts are no-ops when POST_NOTIFICATIONS is denied.
 */
object DownloadNotifier {
    const val CHANNEL_ID = "yts_downloads"
    private const val CHANNEL_NAME = "Downloads"
    private const val CHANNEL_DESC = "On-device yt-dlp download progress and results"

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val mgr = context.getSystemService(NotificationManager::class.java) ?: return
        val existing = mgr.getNotificationChannel(CHANNEL_ID)
        if (existing != null) return
        val channel =
            NotificationChannel(CHANNEL_ID, CHANNEL_NAME, NotificationManager.IMPORTANCE_LOW).apply {
                description = CHANNEL_DESC
            }
        mgr.createNotificationChannel(channel)
    }

    fun canPost(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true
        return ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.POST_NOTIFICATIONS,
        ) == PackageManager.PERMISSION_GRANTED
    }

    fun notifyProgress(context: Context, url: String, title: String, percent: Int) {
        if (!canPost(context)) return
        ensureChannel(context)
        val label = title.ifBlank { url }
        val notification =
            baseBuilder(context, url)
                .setContentTitle(label)
                .setContentText(context.getString(R.string.notif_downloading, percent.coerceIn(0, 100)))
                .setProgress(100, percent.coerceIn(0, 100), percent <= 0)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .build()
        NotificationManagerCompat.from(context).notify(notifId(url), notification)
    }

    fun notifyDone(context: Context, url: String, title: String, fileName: String) {
        if (!canPost(context)) return
        ensureChannel(context)
        val label = title.ifBlank { url }
        val notification =
            baseBuilder(context, url)
                .setContentTitle(label)
                .setContentText(context.getString(R.string.notif_done, fileName))
                .setProgress(0, 0, false)
                .setOngoing(false)
                .setAutoCancel(true)
                .build()
        NotificationManagerCompat.from(context).notify(notifId(url), notification)
    }

    fun notifyError(context: Context, url: String, title: String, error: String) {
        if (!canPost(context)) return
        ensureChannel(context)
        val label = title.ifBlank { url }
        val detail = error.ifBlank { "unknown error" }.take(160)
        val notification =
            baseBuilder(context, url)
                .setContentTitle(label)
                .setContentText(context.getString(R.string.notif_failed, detail))
                .setProgress(0, 0, false)
                .setOngoing(false)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .build()
        NotificationManagerCompat.from(context).notify(notifId(url), notification)
    }

    fun cancel(context: Context, url: String) {
        NotificationManagerCompat.from(context).cancel(notifId(url))
    }

    /** Stable positive id from URL — host-testable. */
    fun notifId(url: String): Int {
        val h = url.trim().lowercase().hashCode()
        return if (h == Int.MIN_VALUE) 1 else kotlin.math.abs(h).coerceAtLeast(1)
    }

    private fun baseBuilder(context: Context, url: String): NotificationCompat.Builder {
        val open =
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
                action = Intent.ACTION_MAIN
                addCategory(Intent.CATEGORY_LAUNCHER)
            }
        val pending =
            PendingIntent.getActivity(
                context,
                notifId(url),
                open,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
        return NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_download)
            .setContentIntent(pending)
            .setCategory(NotificationCompat.CATEGORY_PROGRESS)
            .setPriority(NotificationCompat.PRIORITY_LOW)
    }
}
