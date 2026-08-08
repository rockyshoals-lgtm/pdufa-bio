import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { Alarm } from '../types';
import { cancelNative, scheduleNative, scheduleNativeSnooze } from './nativeAlarm';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function ensurePermissions(): Promise<boolean> {
  const settings = await Notifications.getPermissionsAsync();
  if (settings.granted) return true;
  const req = await Notifications.requestPermissionsAsync({
    ios: { allowAlert: true, allowSound: true, allowBadge: false },
  });
  return req.granted;
}

export async function setupAndroidChannel(): Promise<void> {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync('alarms', {
    name: 'Alarms',
    importance: Notifications.AndroidImportance.MAX,
    sound: 'default',
    vibrationPattern: [0, 500, 500, 500],
    bypassDnd: true,
    lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
  });
}

function content(alarm: Alarm) {
  return {
    title: '⏰ WakeQuest — your monster needs you!',
    body: alarm.label
      ? `${alarm.label} — tap to start your wake-up challenge`
      : 'Tap to start your wake-up challenge and save your streak',
    sound: 'default' as const,
    data: { alarmId: alarm.id },
  };
}

const CHANNEL = Platform.OS === 'android' ? { channelId: 'alarms' } : {};

/**
 * Schedule an alarm. On Android with the native module (dev client / production build),
 * a Doze-proof AlarmManager.setAlarmClock alarm fires a full-screen native ring UI.
 * Notifications are ALSO scheduled everywhere as the cross-platform safety net.
 * Returns notification ids.
 */
export async function scheduleAlarm(alarm: Alarm): Promise<string[]> {
  scheduleNative(alarm);
  const ids: string[] = [];
  if (alarm.days.length === 0) {
    // one-shot: next occurrence of hour:minute
    const now = new Date();
    const fire = new Date(now);
    fire.setHours(alarm.hour, alarm.minute, 0, 0);
    if (fire <= now) fire.setDate(fire.getDate() + 1);
    ids.push(
      await Notifications.scheduleNotificationAsync({
        content: content(alarm),
        trigger: { date: fire, ...CHANNEL },
      })
    );
  } else {
    for (const day of alarm.days) {
      ids.push(
        await Notifications.scheduleNotificationAsync({
          content: content(alarm),
          trigger: {
            weekday: day + 1, // expo: 1 = Sunday
            hour: alarm.hour,
            minute: alarm.minute,
            repeats: true,
            ...CHANNEL,
          },
        })
      );
    }
  }
  return ids;
}

export async function cancelAlarm(notificationIds: string[], alarm?: Alarm): Promise<void> {
  if (alarm) cancelNative(alarm);
  await Promise.all(notificationIds.map((id) => Notifications.cancelScheduledNotificationAsync(id).catch(() => {})));
}

/** Snooze: one-shot notification (+ native alarm on Android) N minutes from now. */
export async function scheduleSnooze(alarm: Alarm, minutes = 5): Promise<string> {
  scheduleNativeSnooze(alarm, minutes);
  return Notifications.scheduleNotificationAsync({
    content: { ...content(alarm), title: '😤 Snooze over. Your monster remembers.' },
    trigger: { seconds: minutes * 60, ...CHANNEL },
  });
}

/** Nightly "protect your streak" reminder. Returns notification id. */
export async function scheduleBedtimeReminder(hour: number, minute: number): Promise<string> {
  return Notifications.scheduleNotificationAsync({
    content: {
      title: '🌙 Bedtime — your streak is counting on you',
      body: 'Wind down now so tomorrow-you wakes up a winner. Your monster is already yawning.',
      sound: 'default',
      data: {},
    },
    trigger: { hour, minute, repeats: true, ...CHANNEL },
  });
}

export async function cancelBedtimeReminder(notifId: string | null): Promise<void> {
  if (notifId) await Notifications.cancelScheduledNotificationAsync(notifId).catch(() => {});
}

export function formatTime(hour: number, minute: number): string {
  const h12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${h12}:${String(minute).padStart(2, '0')}`;
}

export function ampm(hour: number): string {
  return hour < 12 ? 'AM' : 'PM';
}

export const DAY_LETTERS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
