import React, { useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { MonsterAvatar } from '../components/MonsterAvatar';
import { NeonButton } from '../components/NeonButton';
import { GlassCard } from '../components/GlassCard';
import { colors, radius, spacing, type } from '../theme/theme';
import { decodeBattlePayload, simulateBattle, Fighter } from '../logic/battle';
import { getSpecies } from '../logic/monsters';
import { RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'Battle'>;

function HpBar({ hp, maxHp, color }: { hp: number; maxHp: number; color: string }) {
  const pct = Math.max(0, hp / maxHp);
  return (
    <View style={styles.hpTrack}>
      <View style={[styles.hpFill, { width: `${pct * 100}%`, backgroundColor: pct > 0.35 ? color : colors.red }]} />
    </View>
  );
}

function FighterCard({ f, hp, maxHp, active }: { f: Fighter; hp: number; maxHp: number; active: boolean }) {
  const species = getSpecies(f.speciesId);
  return (
    <View style={[styles.fighter, active && styles.fighterActive]}>
      <MonsterAvatar species={species} stage={f.stage} energy={hp > 0 ? f.energy : 0} size={84} />
      <Text style={[type.h2, { fontSize: 16, marginTop: 8 }]} numberOfLines={1}>
        {f.name}
      </Text>
      <Text style={[type.label, { marginBottom: 6 }]}>
        Stg {f.stage} · 🔥{f.streak}
      </Text>
      <HpBar hp={hp} maxHp={maxHp} color={species.colors[0]} />
      <Text style={[type.body, { fontSize: 12, marginTop: 4 }]}>
        {Math.max(0, hp)}/{maxHp} HP
      </Text>
    </View>
  );
}

export function BattleScreen() {
  const nav = useNavigation<Nav>();
  const { params } = useRoute<Route>();

  const me = useMemo(() => decodeBattlePayload(params.me), [params.me]);
  const opponent = useMemo(() => decodeBattlePayload(params.opponent), [params.opponent]);
  const result = useMemo(() => (me && opponent ? simulateBattle(me, opponent) : null), [me, opponent]);

  const [turnIndex, setTurnIndex] = useState(-1);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!result) return;
    if (turnIndex >= result.turns.length - 1) {
      const t = setTimeout(() => setDone(true), 900);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => {
      const turn = result.turns[turnIndex + 1];
      if (turn && !turn.miss) {
        Haptics.impactAsync(
          turn.crit ? Haptics.ImpactFeedbackStyle.Heavy : Haptics.ImpactFeedbackStyle.Light
        ).catch(() => {});
      }
      setTurnIndex((i) => i + 1);
    }, turnIndex < 0 ? 1200 : 1100);
    return () => clearTimeout(t);
  }, [turnIndex, result]);

  if (!me || !opponent || !result) {
    return (
      <View style={[styles.screen, { justifyContent: 'center' }]}>
        <Text style={[type.h2, { textAlign: 'center' }]}>Invalid battle code 😵</Text>
        <NeonButton title="Back" variant="ghost" onPress={() => nav.goBack()} style={{ marginTop: spacing.lg }} />
      </View>
    );
  }

  const currentHp: [number, number] =
    turnIndex < 0 ? [result.maxHp[0], result.maxHp[1]] : result.turns[Math.min(turnIndex, result.turns.length - 1)].hp;
  const currentTurn = turnIndex >= 0 ? result.turns[Math.min(turnIndex, result.turns.length - 1)] : null;
  const winnerName = result.winner === -1 ? null : result.winner === 0 ? me.name : opponent.name;
  const iWon = result.winner === 0;

  return (
    <LinearGradient colors={['#1A0B2E', colors.bg]} style={styles.screen}>
      <Text style={[type.label, { textAlign: 'center', marginBottom: spacing.md }]}>MONSTER BATTLE</Text>

      <View style={styles.arena}>
        <FighterCard f={me} hp={currentHp[0]} maxHp={result.maxHp[0]} active={currentTurn?.attacker === 0} />
        <Text style={styles.vs}>VS</Text>
        <FighterCard f={opponent} hp={currentHp[1]} maxHp={result.maxHp[1]} active={currentTurn?.attacker === 1} />
      </View>

      <GlassCard style={{ marginTop: spacing.lg, minHeight: 76 }} padding={14}>
        <Text style={[type.body, { textAlign: 'center' }]}>
          {done
            ? winnerName
              ? `🏆 ${winnerName} WINS!`
              : '🤝 A draw. Both went back to bed.'
            : currentTurn
              ? currentTurn.line
              : 'The monsters size each other up…'}
        </Text>
      </GlassCard>

      {done && (
        <View style={{ marginTop: spacing.lg }}>
          <Text style={[type.body, { textAlign: 'center', marginBottom: spacing.md }]}>
            {result.winner === -1
              ? 'Evenly matched. Settle it tomorrow morning.'
              : iWon
                ? 'Your wake-up discipline just paid off. Tell them to snooze less.'
                : 'Defeat. You know exactly how to fix this: wake up on time.'}
          </Text>
          <NeonButton title="Done" onPress={() => nav.goBack()} />
        </View>
      )}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, padding: spacing.lg, paddingTop: 84 },
  arena: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  fighter: {
    flex: 1,
    alignItems: 'center',
    padding: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  fighterActive: { borderColor: 'rgba(255,255,255,0.25)', backgroundColor: 'rgba(255,255,255,0.04)' },
  vs: { color: colors.textDim, fontWeight: '800', fontSize: 18, marginHorizontal: 6 },
  hpTrack: {
    height: 8,
    width: '100%',
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.08)',
    overflow: 'hidden',
  },
  hpFill: { height: '100%', borderRadius: 999 },
});
