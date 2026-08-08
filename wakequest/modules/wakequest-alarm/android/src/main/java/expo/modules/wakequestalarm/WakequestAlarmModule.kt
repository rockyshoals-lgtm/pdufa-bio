package expo.modules.wakequestalarm

import android.app.AlarmManager
import android.content.Context
import android.os.Build
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class WakequestAlarmModule : Module() {
  private val context: Context
    get() = requireNotNull(appContext.reactContext) { "React context is null" }

  override fun definition() = ModuleDefinition {
    Name("WakequestAlarm")

    /** Schedule an exact, Doze-proof alarm. timestamp = epoch millis. */
    Function("setAlarm") { id: String, timestamp: Double, label: String, repeatWeekly: Boolean ->
      AlarmStore.schedule(context, AlarmStore.StoredAlarm(id, timestamp.toLong(), label, repeatWeekly))
    }

    Function("cancelAlarm") { id: String ->
      AlarmStore.cancel(context, id)
    }

    Function("cancelAll") {
      AlarmStore.cancelAll(context)
    }

    /**
     * If the app was opened from the native ring screen, returns the alarm id (once),
     * so JS can navigate straight to the challenge.
     */
    Function("getLaunchAlarmId") {
      val activity = appContext.currentActivity ?: return@Function null
      val id = activity.intent?.getStringExtra("wakequest_alarm_id")
      if (id != null) activity.intent?.removeExtra("wakequest_alarm_id")
      id
    }

    /** setAlarmClock is exempt from the exact-alarm permission, but expose the check anyway. */
    Function("canUseExactAlarms") {
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        am.canScheduleExactAlarms()
      } else {
        true
      }
    }
  }
}
