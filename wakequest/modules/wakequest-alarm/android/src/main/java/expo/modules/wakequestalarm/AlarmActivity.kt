package expo.modules.wakequestalarm

import android.app.Activity
import android.app.KeyguardManager
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.media.AudioAttributes
import android.media.Ringtone
import android.media.RingtoneManager
import android.os.Build
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.view.Gravity
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.core.app.NotificationManagerCompat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Native full-screen ring UI. Shows over the lock screen, turns the screen on,
 * loops the system alarm sound on the ALARM audio stream, and vibrates —
 * even if the React Native app process was killed.
 * "START CHALLENGE" wakes the RN app with the alarm id so JS takes over.
 */
class AlarmActivity : Activity() {
  private var ringtone: Ringtone? = null
  private var vibrator: Vibrator? = null

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
      setShowWhenLocked(true)
      setTurnScreenOn(true)
      (getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager).requestDismissKeyguard(this, null)
    } else {
      @Suppress("DEPRECATION")
      window.addFlags(
        WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
          WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
          WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
      )
    }
    window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

    val alarmId = intent.getStringExtra("alarmId") ?: ""
    val label = intent.getStringExtra("label") ?: ""

    buildUi(alarmId, label)
    startNoise()
  }

  private fun buildUi(alarmId: String, label: String) {
    val root = LinearLayout(this).apply {
      orientation = LinearLayout.VERTICAL
      gravity = Gravity.CENTER
      setBackgroundColor(Color.parseColor("#070B14"))
      setPadding(48, 48, 48, 48)
    }

    root.addView(TextView(this).apply {
      text = "⏰"
      textSize = 64f
      gravity = Gravity.CENTER
    })

    root.addView(TextView(this).apply {
      text = SimpleDateFormat("h:mm", Locale.getDefault()).format(Date())
      textSize = 72f
      setTextColor(Color.parseColor("#F4F6FB"))
      typeface = Typeface.create("sans-serif-thin", Typeface.NORMAL)
      gravity = Gravity.CENTER
    })

    if (label.isNotEmpty()) {
      root.addView(TextView(this).apply {
        text = label
        textSize = 18f
        setTextColor(Color.parseColor("#9AA1B5"))
        gravity = Gravity.CENTER
        setPadding(0, 16, 0, 0)
      })
    }

    root.addView(TextView(this).apply {
      text = "Your monster is counting on you."
      textSize = 14f
      setTextColor(Color.parseColor("#5E6577"))
      gravity = Gravity.CENTER
      setPadding(0, 24, 0, 48)
    })

    root.addView(Button(this).apply {
      text = "⚔️  START CHALLENGE"
      textSize = 18f
      setTextColor(Color.WHITE)
      setBackgroundColor(Color.parseColor("#8B5CF6"))
      setPadding(64, 40, 64, 40)
      setOnClickListener { openApp(alarmId) }
    })

    setContentView(root)
  }

  private fun startNoise() {
    try {
      val uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
        ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
      ringtone = RingtoneManager.getRingtone(this, uri)?.apply {
        audioAttributes = AudioAttributes.Builder()
          .setUsage(AudioAttributes.USAGE_ALARM)
          .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
          .build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) isLooping = true
        play()
      }
    } catch (ignored: Exception) {}

    try {
      @Suppress("DEPRECATION")
      vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
      val pattern = longArrayOf(0, 600, 400, 600, 400)
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        vibrator?.vibrate(VibrationEffect.createWaveform(pattern, 0))
      } else {
        @Suppress("DEPRECATION")
        vibrator?.vibrate(pattern, 0)
      }
    } catch (ignored: Exception) {}
  }

  private fun stopNoise() {
    try { ringtone?.stop() } catch (ignored: Exception) {}
    try { vibrator?.cancel() } catch (ignored: Exception) {}
    ringtone = null
    vibrator = null
  }

  private fun openApp(alarmId: String) {
    stopNoise()
    try { NotificationManagerCompat.from(this).cancel(alarmId.hashCode()) } catch (ignored: Exception) {}
    val launch = packageManager.getLaunchIntentForPackage(packageName)?.apply {
      putExtra("wakequest_alarm_id", alarmId)
      addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP)
    }
    if (launch != null) startActivity(launch)
    finish()
  }

  // Block back button — the only way out is the challenge
  @Deprecated("Deprecated in Java")
  override fun onBackPressed() {}

  override fun onDestroy() {
    stopNoise()
    super.onDestroy()
  }
}
