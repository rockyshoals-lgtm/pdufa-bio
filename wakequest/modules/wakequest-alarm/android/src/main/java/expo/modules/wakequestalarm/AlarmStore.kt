package expo.modules.wakequestalarm

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import org.json.JSONObject

/**
 * Persists scheduled alarms (SharedPreferences) and talks to AlarmManager.
 * setAlarmClock() is used deliberately: it is exempt from Doze/battery optimization
 * and shows the system alarm indicator — the same mechanism as the stock clock app.
 */
object AlarmStore {
  private const val PREFS = "wakequest_native_alarms"

  data class StoredAlarm(val id: String, val timestamp: Long, val label: String, val repeatWeekly: Boolean)

  private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

  fun all(context: Context): List<StoredAlarm> =
    prefs(context).all.values.mapNotNull { raw ->
      try {
        val o = JSONObject(raw as String)
        StoredAlarm(
          o.getString("id"),
          o.getLong("timestamp"),
          o.optString("label", ""),
          o.optBoolean("repeatWeekly", false)
        )
      } catch (e: Exception) {
        null
      }
    }

  fun get(context: Context, id: String): StoredAlarm? =
    all(context).firstOrNull { it.id == id }

  private fun firePendingIntent(context: Context, a: StoredAlarm): PendingIntent {
    val intent = Intent(context, AlarmReceiver::class.java).apply {
      putExtra("alarmId", a.id)
      putExtra("label", a.label)
      putExtra("repeatWeekly", a.repeatWeekly)
    }
    return PendingIntent.getBroadcast(
      context,
      a.id.hashCode(),
      intent,
      PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )
  }

  fun schedule(context: Context, a: StoredAlarm) {
    val json = JSONObject()
      .put("id", a.id)
      .put("timestamp", a.timestamp)
      .put("label", a.label)
      .put("repeatWeekly", a.repeatWeekly)
    prefs(context).edit().putString(a.id, json.toString()).apply()

    val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
    val launch = context.packageManager.getLaunchIntentForPackage(context.packageName)
    val showPi = PendingIntent.getActivity(
      context, 0, launch, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )
    am.setAlarmClock(AlarmManager.AlarmClockInfo(a.timestamp, showPi), firePendingIntent(context, a))
  }

  fun cancel(context: Context, id: String) {
    val existing = get(context, id)
    prefs(context).edit().remove(id).apply()
    val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
    val pi = firePendingIntent(context, existing ?: StoredAlarm(id, 0L, "", false))
    am.cancel(pi)
    pi.cancel()
  }

  fun cancelAll(context: Context) {
    all(context).forEach { cancel(context, it.id) }
  }

  /** Called after a repeating alarm fires: schedule the same alarm one week later. */
  fun rescheduleWeekly(context: Context, id: String) {
    val a = get(context, id) ?: return
    schedule(context, a.copy(timestamp = a.timestamp + 7L * 24 * 60 * 60 * 1000))
  }

  /** Called on boot: re-register everything still in the future; bump past weekly repeats forward. */
  fun rescheduleAll(context: Context) {
    val now = System.currentTimeMillis()
    all(context).forEach { a ->
      var ts = a.timestamp
      if (ts <= now && a.repeatWeekly) {
        val week = 7L * 24 * 60 * 60 * 1000
        while (ts <= now) ts += week
      }
      if (ts > now) schedule(context, a.copy(timestamp = ts)) else cancel(context, a.id)
    }
  }
}
