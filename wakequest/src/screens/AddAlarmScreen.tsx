import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useStore } from '../state/store';
import { GlassCard } from '../components/GlassCard';
import { NeonButton } from '../components/NeonButton';
import { colors, radius, spacing, type } from '../theme/theme';
import { cancelAlarm, DAY_LETTERS, ensurePermissions, scheduleAlarm } from '../logic/alarms';
import { Alarm, ChallengeType, RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'AddAlarm'>;

const CHALLENGES: { key: ChallengeType; label: string; emoji: string }[] = [
  { key: 'random', label: 'Surprise me', emoji: '🎲' },
  { key: 'math', label: 'Math', emoji: '🧮' },
  { key: 'memory', label: 'Memory', emoji: '🧠' },
  { key: 'shake', label: 'Shake', emoji: '📳' },
  { key: 'typing', label: 'Typing', emoji: '⌨️' },
];

function Stepper({ value, onChange, max }: { value: number; onChange: (v: number) => void; max: number }) {
  const step = (d: number) => onChange((value + d + max) % max);
  return (
    <View style={styles.stepper}>
      <Pressable onPress={() => step(1)} style={styles.stepBtn}>
        <Text style={styles.stepBtnText}>▲</Text>
      </Pressable>
      <Text style={styles.stepValue}>{String(value).padStart(2, '0')}</Text>
      <Pressable onPress={() => step(-1)} style={styles.stepBtn}>
        <Text style={styles.stepBtnText}>▼</Text>
      </Pressable>
    </View>
  );
}

export function AddAlarmScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { alarms, upsertAlarm, removeAlarm } = useStore();
  const existing = alarms.find((a) => a.id === route.params?.alarmId);

  const [hour, setHour] = useState(existing?.hour ?? 7);
  const [minute, setMinute] = useState(existing?.minute ?? 0);
  const [label, setLabel] = useState(existing?.label ?? '');
  const [days, setDays] = useState<number[]>(existing?.days ?? [1, 2, 3, 4, 5]);
  const [challenge, setChallenge] = useState<ChallengeType>(existing?.challenge ?? 'random');

  const toggleDay = (i: number) =>
    setDays((d) => (d.includes(i) ? d.filter((x) => x !== i) : [...d, i].sort()));

  const save = async () => {
    const ok = await ensurePermissions();
    const alarm: Alarm = {
      id: existing?.id ?? String(Date.now()),
      hour,
      minute,
      label: label.trim(),
      days,
      enabled: ok,
      challenge,
      notificationIds: [],
    };
    if (existing) await cancelAlarm(existing.notificationIds, existing);
    if (ok) alarm.notificationIds = await scheduleAlarm(alarm);
    upsertAlarm(alarm);
    nav.goBack();
  };

  const del = async () => {
    if (existing) {
      await cancelAlarm(existing.notificationIds, existing);
      removeAlarm(existing.id);
    }
    nav.goBack();
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ padding: spacing.lg, paddingTop: 64 }}>
      <Text style={[type.h1, { marginBottom: spacing.lg }]}>{existing ? 'Edit Alarm' : 'New Alarm'}</Text>

      <GlassCard style={{ marginBottom: spacing.md }}>
        <View style={styles.timeRow}>
          <Stepper value={hour} onChange={setHour} max={24} />
          <Text style={styles.colon}>:</Text>
          <Stepper value={minute} onChange={setMinute} max={60} />
        </View>
      </GlassCard>

      <GlassCard style={{ marginBottom: spacing.md }}>
        <Text style={[type.label, { marginBottom: spacing.sm }]}>Repeat</Text>
        <View style={styles.dayRow}>
          {DAY_LETTERS.map((d, i) => (
            <Pressable
              key={i}
              onPress={() => toggleDay(i)}
              style={[styles.dayChip, days.includes(i) && styles.dayChipOn]}
            >
              <Text style={[styles.dayChipText, days.includes(i) && { color: '#fff' }]}>{d}</Text>
            </Pressable>
          ))}
        </View>
      </GlassCard>

      <GlassCard style={{ marginBottom: spacing.md }}>
        <Text style={[type.label, { marginBottom: spacing.sm }]}>Wake-up challenge</Text>
        <View style={styles.chRow}>
          {CHALLENGES.map((c) => (
            <Pressable
              key={c.key}
              onPress={() => setChallenge(c.key)}
              style={[styles.chChip, challenge === c.key && styles.chChipOn]}
            >
              <Text style={{ fontSize: 18 }}>{c.emoji}</Text>
              <Text style={[styles.chText, challenge === c.key && { color: colors.text }]}>{c.label}</Text>
            </Pressable>
          ))}
        </View>
      </GlassCard>

      <GlassCard style={{ marginBottom: spacing.lg }}>
        <Text style={[type.label, { marginBottom: spacing.sm }]}>Label</Text>
        <TextInput
          value={label}
          onChangeText={setLabel}
          placeholder="e.g. Gym before work"
          placeholderTextColor={colors.textFaint}
          style={styles.input}
        />
      </GlassCard>

      <NeonButton title="Save Alarm" onPress={save} />
      {existing && (
        <NeonButton title="Delete" variant="ghost" onPress={del} style={{ marginTop: spacing.md }} />
      )}
      <NeonButton title="Cancel" variant="ghost" onPress={() => nav.goBack()} style={{ marginTop: spacing.md }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  timeRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
  colon: { fontSize: 56, color: colors.textDim, fontWeight: '200', marginBottom: 6 },
  stepper: { alignItems: 'center' },
  stepBtn: { padding: 8 },
  stepBtnText: { color: colors.cyan, fontSize: 18 },
  stepValue: { fontSize: 64, fontWeight: '200', color: colors.text, letterSpacing: -2, minWidth: 90, textAlign: 'center' },
  dayRow: { flexDirection: 'row', justifyContent: 'space-between' },
  dayChip: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  dayChipOn: { backgroundColor: colors.violet },
  dayChipText: { color: colors.textDim, fontWeight: '600' },
  chRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  chChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: radius.pill,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  chChipOn: { backgroundColor: 'rgba(139,92,246,0.35)', borderWidth: 1, borderColor: colors.violet },
  chText: { color: colors.textDim, fontWeight: '600', fontSize: 13 },
  input: {
    color: colors.text,
    fontSize: 16,
    paddingVertical: 10,
    paddingHorizontal: 14,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: radius.sm,
  },
});
