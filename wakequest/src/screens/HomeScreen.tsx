import React from 'react';
import { FlatList, Pressable, StyleSheet, Switch, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useStore } from '../state/store';
import { GlassCard } from '../components/GlassCard';
import { NeonButton } from '../components/NeonButton';
import { XPBar } from '../components/XPBar';
import { colors, spacing, type } from '../theme/theme';
import { ampm, cancelAlarm, DAY_LETTERS, ensurePermissions, formatTime, scheduleAlarm } from '../logic/alarms';
import { dailyLine, getSpecies } from '../logic/monsters';
import { Alarm, RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function HomeScreen() {
  const nav = useNavigation<Nav>();
  const { alarms, xp, streak, setAlarmEnabled, speciesId, petName } = useStore();
  const species = getSpecies(speciesId);
  const monsterName = petName || species.name;

  const toggle = async (alarm: Alarm) => {
    if (alarm.enabled) {
      await cancelAlarm(alarm.notificationIds, alarm);
      setAlarmEnabled(alarm.id, false, []);
    } else {
      const ok = await ensurePermissions();
      if (!ok) return;
      const ids = await scheduleAlarm(alarm);
      setAlarmEnabled(alarm.id, true, ids);
    }
  };

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={type.h1}>WakeQuest</Text>
        <View style={styles.streakPill}>
          <Text style={styles.streakText}>🔥 {streak}</Text>
        </View>
      </View>

      <GlassCard style={{ marginBottom: spacing.md }}>
        <XPBar xp={xp} />
      </GlassCard>

      <GlassCard style={{ marginBottom: spacing.lg }} padding={14}>
        <Text style={styles.monsterLine}>
          {monsterName}: “{dailyLine(species.dialogue.greeting)}”
        </Text>
      </GlassCard>

      <Text style={[type.label, { marginBottom: spacing.sm }]}>Alarms</Text>

      <FlatList
        data={alarms}
        keyExtractor={(a) => a.id}
        contentContainerStyle={{ paddingBottom: 120 }}
        ListEmptyComponent={
          <GlassCard style={{ alignItems: 'center' }} padding={28}>
            <Text style={{ fontSize: 40, marginBottom: 8 }}>🌙</Text>
            <Text style={type.h2}>No alarms yet</Text>
            <Text style={[type.body, { textAlign: 'center', marginTop: 6 }]}>
              Set one — {monsterName} evolves every time you wake up.
            </Text>
          </GlassCard>
        }
        renderItem={({ item }) => (
          <Pressable
            onPress={() => nav.navigate('AddAlarm', { alarmId: item.id })}
            onLongPress={() => nav.navigate('Ring', { alarmId: item.id })}
          >
            <GlassCard style={{ marginBottom: spacing.md, opacity: item.enabled ? 1 : 0.55 }}>
              <View style={styles.alarmRow}>
                <View>
                  <Text style={styles.time}>
                    {formatTime(item.hour, item.minute)}
                    <Text style={styles.ampm}> {ampm(item.hour)}</Text>
                  </Text>
                  {!!item.label && <Text style={type.body}>{item.label}</Text>}
                  <View style={styles.days}>
                    {DAY_LETTERS.map((d, i) => (
                      <Text
                        key={i}
                        style={[styles.day, item.days.includes(i) && { color: colors.cyan, fontWeight: '700' }]}
                      >
                        {d}
                      </Text>
                    ))}
                  </View>
                </View>
                <Switch
                  value={item.enabled}
                  onValueChange={() => toggle(item)}
                  trackColor={{ true: colors.violet, false: 'rgba(255,255,255,0.15)' }}
                  thumbColor="#fff"
                />
              </View>
            </GlassCard>
          </Pressable>
        )}
      />

      <View style={styles.fab}>
        <NeonButton title="+  New Alarm" onPress={() => nav.navigate('AddAlarm')} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg, paddingHorizontal: spacing.lg, paddingTop: 64 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg },
  streakPill: {
    backgroundColor: 'rgba(251,191,36,0.12)',
    borderColor: 'rgba(251,191,36,0.35)',
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  streakText: { color: colors.amber, fontWeight: '700', fontSize: 15 },
  monsterLine: { ...type.body, fontStyle: 'italic', color: colors.textDim },
  alarmRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  time: { fontSize: 38, fontWeight: '200', color: colors.text, letterSpacing: -1 },
  ampm: { fontSize: 16, color: colors.textDim, fontWeight: '500' },
  days: { flexDirection: 'row', gap: 8, marginTop: 6 },
  day: { color: colors.textFaint, fontSize: 12, fontWeight: '500' },
  fab: { position: 'absolute', bottom: 28, left: spacing.lg, right: spacing.lg },
});
