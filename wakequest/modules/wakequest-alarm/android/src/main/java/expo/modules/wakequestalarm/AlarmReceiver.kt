package expo.modules.wakequestalarm

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

/**
 * Fires when AlarmManager triggers. Posts a full-screen-intent notification —
 * the OS-sanctioned way to launch the ring UI over the lock screen, even when
 * the app process is dead.
 */
class AlarmReceiver : BroadcastReceiver() {
  companion object {
    const val CHANNEL_ID = "wakequest_native_alarm"
  }

  override fun onReceive(context: Context, intent: Intent) {
    val alarmId = intent.getStringExtra("alarmId") ?: return
    val label = intent.getStringExtra("label") ?: ""
    val repeatWeekly = intent.getBooleanExtra("repeatWeekly", false)

    val fullScreenIntent = Intent(context, AlarmActivity::class.java).apply {
      putExtra("alarmId", alarmId)
      putExtra("label", label)
      addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
    }
    val fullScreenPi = PendingIntent.getActivity(
      context,
      alarmId.hashCode(),
      fullScreenIntent,
      PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
      if (nm.getNotificationChannel(CHANNEL_ID) == null) {
        val channel = NotificationChannel(CHANNEL_ID, "Alarms (reliable)", NotificationManager.IMPORTANCE_HIGH).apply {
          description = "Full-screen alarms that cannot be missed"
          setSound(null, null) // AlarmActivity owns the sound (looping alarm stream)
          enableVibration(false)
          setBypassDnd(true)
          lockscreenVisibility = android.app.Notification.VISIBILITY_PUBLIC
        }
        nm.createNotificationChannel(channel)
      }
    }

    val notification = NotificationCompat.Builder(context, CHANNEL_ID)
      .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
      .setContentTitle("⏰ WakeQuest")
      .setContentText(if (label.isNotEmpty()) label else "Your monster needs you — start the challenge!")
      .setPriority(NotificationCompat.PRIORITY_MAX)
      .setCategory(NotificationCompat.CATEGORY_ALARM)
      .setFullScreenIntent(fullScreenPi, true)
      .setContentIntent(fullScreenPi)
      .setAutoCancel(true)
      .setOngoing(true)
      .build()

    try {
      NotificationManagerCompat.from(context).notify(alarmId.hashCode(), notification)
    } catch (e: SecurityException) {
      // POST_NOTIFICATIONS not granted — launch the activity directly as a last resort
      try {
        context.startActivity(fullScreenIntent)
      } catch (ignored: Exception) {}
    }

    if (repeatWeekly) {
      AlarmStore.rescheduleWeekly(context, alarmId)
    } else {
      AlarmStore.cancel(context, alarmId)
    }
  }
}
