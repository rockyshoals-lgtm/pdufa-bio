import { requireNativeModule } from 'expo-modules-core';
import { Platform } from 'react-native';

interface WakequestAlarmNative {
  setAlarm(id: string, timestamp: number, label: string, repeatWeekly: boolean): void;
  cancelAlarm(id: string): void;
  cancelAll(): void;
  getLaunchAlarmId(): string | null;
  canUseExactAlarms(): boolean;
}

let native: WakequestAlarmNative | null = null;
if (Platform.OS === 'android') {
  try {
    native = requireNativeModule<WakequestAlarmNative>('WakequestAlarm');
  } catch {
    // Running in Expo Go / iOS — native module unavailable, app falls back to notifications
    native = null;
  }
}

export default native;
