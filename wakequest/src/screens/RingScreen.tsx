import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Easing, StyleSheet, Text, Vibration, View } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import { useStore } from '../state/store';
import { NeonButton } from '../components/NeonButton';
import { colors, gradients, spacing, type } from '../theme/theme';
import { ampm, formatTime, scheduleSnooze } from '../logic/alarms';
import { getSpecies, pickLine } from '../logic/monsters';
import { RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'Ring'>;

const VIBRATION_PATTERN = [0, 600, 400, 600, 400];

export function RingScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { alarms, recordSnooze, streak, speciesId, petName } = useStore();
  const alarm = alarms.find((a) => a.id === route.params.alarmId);
  const species = getSpecies(speciesId);
  const monsterName = petName || species.name;
  const taunt = useMemo(() => pickLine(species.dialogue.ring), [species]);
  const [snoozes, setSnoozes] = useState(0);
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Vibration.vibrate(VIBRATION_PATTERN, true);
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.12, duration: 500, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 500, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      ])
    ).start();
    return () => Vibration.cancel();
  }, [pulse]);

  useEffect(() => {
    if (!alarm) nav.goBack();
  }, [alarm, nav]);

  if (!alarm) return null;

  const snooze = async () => {
    Vibration.cancel();
    recordSnooze();
    setSnoozes((s) => s + 1);
    await scheduleSnooze(alarm, 5);
    nav.navigate('Tabs');
  };

  const startChallenge = () => {
    Vibration.cancel();
    nav.replace('Challenge', { alarmId: alarm.id, snoozes });
  };

  return (
    <LinearGradient colors={['#1A0B2E', colors.bg]} style={styles.screen}>
      <View style={styles.center}>
        <Animated.Text style={[styles.bell, { transform: [{ scale: pulse }] }]}>⏰</Animated.Text>
        <Text style={styles.time}>
          {formatTime(alarm.hour, alarm.minute)}
          <Text style={styles.ampm}> {ampm(alarm.hour)}</Text>
        </Text>
        {!!alarm.label && <Text style={[type.h2, { marginTop: 8 }]}>{alarm.label}</Text>}
        <Text style={[type.body, { marginTop: spacing.md, textAlign: 'center', fontStyle: 'italic' }]}>
          {monsterName}: “{taunt}”
        </Text>
        <Text style={[type.body, { marginTop: 8, textAlign: 'center' }]}>🔥 {streak}-day streak on the line.</Text>
      </View>

      <View style={styles.actions}>
        <NeonButton title="⚔️  Start Challenge" onPress={startChallenge} colors={gradients.sunrise} />
        <NeonButton
          title={`Snooze 5 min (${monsterName} will remember this)`}
          variant="ghost"
          onPress={snooze}
          style={{ marginTop: spacing.md }}
        />
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, justifyContent: 'space-between', padding: spacing.lg, paddingBottom: 48 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  bell: { fontSize: 84, marginBottom: spacing.lg },
  time: { ...type.clock },
  ampm: { fontSize: 24, color: colors.textDim, fontWeight: '400' },
  actions: {},
});
