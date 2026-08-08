import React, { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import { useStore } from '../state/store';
import { colors, spacing, type } from '../theme/theme';
import { MathChallenge } from '../challenges/MathChallenge';
import { MemoryChallenge } from '../challenges/MemoryChallenge';
import { ShakeChallenge } from '../challenges/ShakeChallenge';
import { TypingChallenge } from '../challenges/TypingChallenge';
import { ChallengeType, RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'Challenge'>;

const POOL: Exclude<ChallengeType, 'random'>[] = ['math', 'memory', 'shake', 'typing'];

const TITLES: Record<string, string> = {
  math: '🧮 Math Gauntlet',
  memory: '🧠 Memory Match',
  shake: '📳 Shake It Off',
  typing: '⌨️ Wake Typing',
};

export function ChallengeScreen() {
  const nav = useNavigation<Nav>();
  const { params } = useRoute<Route>();
  const { alarms, completeWake } = useStore();
  const alarm = alarms.find((a) => a.id === params.alarmId);

  const kind = useMemo<Exclude<ChallengeType, 'random'>>(() => {
    const c = alarm?.challenge ?? 'random';
    return c === 'random' ? POOL[Math.floor(Math.random() * POOL.length)] : c;
  }, [alarm]);

  const handleDone = (perfect: boolean) => {
    const result = completeWake(params.snoozes, perfect);
    nav.replace('Reward', {
      xp: result.xpGained,
      streak: result.streak,
      leveledUp: result.leveledUp,
      evolvedTo: result.evolvedTo,
      dust: result.dustGained,
      freezeUsed: result.freezeUsed,
    });
  };

  return (
    <LinearGradient colors={['#101B33', colors.bg]} style={styles.screen}>
      <Text style={[type.h1, { marginBottom: 4 }]}>{TITLES[kind]}</Text>
      <Text style={[type.body, { marginBottom: spacing.xl }]}>Complete it to dismiss the alarm</Text>
      <View style={styles.body}>
        {kind === 'math' && <MathChallenge onDone={handleDone} />}
        {kind === 'memory' && <MemoryChallenge onDone={handleDone} />}
        {kind === 'shake' && <ShakeChallenge onDone={handleDone} />}
        {kind === 'typing' && <TypingChallenge onDone={handleDone} />}
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, alignItems: 'center', padding: spacing.lg, paddingTop: 84 },
  body: { flex: 1, width: '100%', alignItems: 'center' },
});
