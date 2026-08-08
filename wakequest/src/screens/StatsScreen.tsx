import React from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';
import { useStore } from '../state/store';
import { GlassCard } from '../components/GlassCard';
import { XPBar } from '../components/XPBar';
import { colors, spacing, type } from '../theme/theme';
import {
  ampm,
  cancelBedtimeReminder,
  ensurePermissions,
  formatTime,
  scheduleBedtimeReminder,
} from '../logic/alarms';

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <GlassCard style={styles.statCard} padding={16}>
      <Text style={[styles.statValue, accent ? { color: accent } : null]}>{value}</Text>
      <Text style={type.label}>{label}</Text>
    </GlassCard>
  );
}

export function StatsScreen() {
  const { xp, streak, bestStreak, totalWakes, totalSnoozes, history, bedtime, setBedtime, streakFreezes } = useStore();

  const toggleBedtime = async (enabled: boolean) => {
    await cancelBedtimeReminder(bedtime.notifId);
    if (enabled) {
      const ok = await ensurePermissions();
      if (!ok) return;
      const notifId = await scheduleBedtimeReminder(bedtime.hour, bedtime.minute);
      setBedtime({ ...bedtime, enabled: true, notifId });
    } else {
      setBedtime({ ...bedtime, enabled: false, notifId: null });
    }
  };

  const shiftBedtime = async (deltaMin: number) => {
    const total = (bedtime.hour * 60 + bedtime.minute + deltaMin + 1440) % 1440;
    const next = { ...bedtime, hour: Math.floor(total / 60), minute: total % 60 };
    if (bedtime.enabled) {
      await cancelBedtimeReminder(bedtime.notifId);
      next.notifId = await scheduleBedtimeReminder(next.hour, next.minute);
    }
    setBedtime(next);
  };
  const onTimeRate = totalWakes > 0 ? Math.round((history.filter((h) => h.onTime).length / Math.max(1, history.length)) * 100) : 0;
  const last14 = history.slice(-14);

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ padding: spacing.lg, paddingTop: 64, paddingBottom: 48 }}>
      <Text style={[type.h1, { marginBottom: spacing.lg }]}>Stats</Text>

      <GlassCard style={{ marginBottom: spacing.md }}>
        <XPBar xp={xp} />
      </GlassCard>

      <View style={styles.grid}>
        <Stat label="Streak" value={`🔥 ${streak}`} accent={colors.amber} />
        <Stat label="Best streak" value={`${bestStreak}`} accent={colors.pink} />
        <Stat label="Total wakes" value={`${totalWakes}`} accent={colors.cyan} />
        <Stat label="Snoozes" value={`${totalSnoozes}`} accent={colors.red} />
        <Stat label="On-time rate" value={`${onTimeRate}%`} accent={colors.green} />
        <Stat label="Total XP" value={`${xp}`} accent={colors.violet} />
      </View>

      <Text style={[type.label, { marginTop: spacing.lg, marginBottom: spacing.sm }]}>Streak protection</Text>
      <GlassCard style={{ marginBottom: spacing.md }}>
        <View style={styles.bedRow}>
          <View style={{ flex: 1 }}>
            <Text style={type.h2}>🌙 Bedtime reminder</Text>
            <Text style={[type.body, { marginTop: 4 }]}>
              {formatTime(bedtime.hour, bedtime.minute)} {ampm(bedtime.hour)} nightly · 🧊 {streakFreezes} freeze
              {streakFreezes === 1 ? '' : 's'} banked
            </Text>
          </View>
          <Switch
            value={bedtime.enabled}
            onValueChange={toggleBedtime}
            trackColor={{ true: colors.violet, false: 'rgba(255,255,255,0.15)' }}
            thumbColor="#fff"
          />
        </View>
        <View style={styles.bedButtons}>
          <Pressable onPress={() => shiftBedtime(-30)} style={styles.bedBtn}>
            <Text style={styles.bedBtnText}>−30 min</Text>
          </Pressable>
          <Pressable onPress={() => shiftBedtime(30)} style={styles.bedBtn}>
            <Text style={styles.bedBtnText}>+30 min</Text>
          </Pressable>
        </View>
      </GlassCard>

      <Text style={[type.label, { marginBottom: spacing.sm }]}>Last 14 days</Text>
      <GlassCard>
        <View style={styles.dots}>
          {Array.from({ length: 14 }).map((_, i) => {
            const rec = last14[i - (14 - last14.length)];
            const color = !rec ? 'rgba(255,255,255,0.08)' : rec.onTime ? colors.green : colors.amber;
            return <View key={i} style={[styles.dot, { backgroundColor: color }]} />;
          })}
        </View>
        <View style={styles.legend}>
          <Text style={type.body}>● on time</Text>
          <Text style={[type.body, { color: colors.amber }]}>● snoozed</Text>
          <Text style={[type.body, { color: colors.textFaint }]}>● missed</Text>
        </View>
      </GlassCard>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  statCard: { flexBasis: '30%', flexGrow: 1, alignItems: 'center' },
  statValue: { fontSize: 24, fontWeight: '700', color: colors.text, marginBottom: 4 },
  dots: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, justifyContent: 'center' },
  dot: { width: 18, height: 18, borderRadius: 9 },
  legend: { flexDirection: 'row', gap: 16, justifyContent: 'center', marginTop: 14 },
  bedRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  bedButtons: { flexDirection: 'row', gap: 10, marginTop: 12 },
  bedBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  bedBtnText: { color: colors.textDim, fontWeight: '600', fontSize: 13 },
});
