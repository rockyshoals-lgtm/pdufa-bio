package expo.modules.wakequestalarm

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** AlarmManager registrations are wiped on reboot — re-register everything we persisted. */
class BootReceiver : BroadcastReceiver() {
  override fun onReceive(context: Context, intent: Intent) {
    val action = intent.action ?: return
    if (action == Intent.ACTION_BOOT_COMPLETED || action == "android.intent.action.QUICKBOOT_POWERON") {
      AlarmStore.rescheduleAll(context)
    }
  }
}
