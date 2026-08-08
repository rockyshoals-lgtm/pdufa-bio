// JS wrapper around the native Android AlarmManager module.
// Falls back silently when unavailable (iOS, Expo Go) — expo-notifications remains the safety net.
import native from '../../modules/wakequest-alarm';
import { Alarm } from '../types';

export const nativeAlarmsAvailable = native != null;

function nextOccurrence(hour: number, minute: number, weekday?: number): number {
  const now = new Date();
  const fire = new Date(now);
  fire.setHours(hour, minute, 0, 0);
  if (weekday === undefined) {
    if (fire <= now) fire.setDate(fire.getDate() + 1);
  } else {
    let delta = (weekday - fire.getDay() + 7) % 7;
    if (delta === 0 && fire <= now) delta = 7;
    fire.setDate(fire.getDate() + delta);
  }
  return fire.getTime();
}

/** Schedule Doze-proof native alarms for every occurrence of this alarm. */
export function scheduleNative(alarm: Alarm): void {
  if (!native) return;
  try {
    if (alarm.days.length === 0) {
      native.setAlarm(alarm.id, nextOccurrence(alarm.hour, alarm.minute), alarm.label, false);
    } else {
      for (const day of alarm.days) {
        native.setAlarm(`${alarm.id}:${day}`, nextOccurrence(alarm.hour, alarm.minute, day), alarm.label, true);
      }
    }
  } catch {}
}

export function cancelNative(alarm: Alarm): void {
  if (!native) return;
  try {
    native.cancelAlarm(alarm.id);
    native.cancelAlarm(`${alarm.id}:snooze`);
    for (let day = 0; day < 7; day++) native.cancelAlarm(`${alarm.id}:${day}`);
  } catch {}
}

export function scheduleNativeSnooze(alarm: Alarm, minutes: number): void {
  if (!native) return;
  try {
    native.setAlarm(`${alarm.id}:snooze`, Date.now() + minutes * 60_000, alarm.label, false);
  } catch {}
}

/** If Android launched us from the native ring screen, returns the store alarm id. */
export function getNativeLaunchAlarmId(): string | null {
  if (!native) return null;
  try {
    const raw = native.getLaunchAlarmId();
    return raw ? raw.split(':')[0] : null;
  } catch {
    return null;
  }
}
