import React, { useEffect, useRef } from 'react';
import { Animated, Share, StyleSheet, Text, View } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { useStore } from '../state/store';
import { NeonButton } from '../components/NeonButton';
import { MonsterAvatar } from '../components/MonsterAvatar';
import { colors, spacing, type } from '../theme/theme';
import { getSpecies, pickLine, stageForPower } from '../logic/monsters';
import { RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'Reward'>;

export function RewardScreen() {
  const nav = useNavigation<Nav>();
  const { params } = useRoute<Route>();
  const { petEnergy, petName, speciesId, wakePower } = useStore();
  const species = getSpecies(speciesId);
  const monsterName = petName || species.name;
  const stage = stageForPower(wakePower);
  const praise = React.useMemo(() => pickLine(species.dialogue.praise), [species]);
  const scale = useRef(new Animated.Value(0.3)).current;
  const fade = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    Animated.parallel([
      Animated.spring(scale, { toValue: 1, friction: 4, useNativeDriver: true }),
      Animated.timing(fade, { toValue: 1, duration: 700, useNativeDriver: true }),
    ]).start();
  }, [scale, fade]);

  return (
    <LinearGradient colors={['#0E1B2E', colors.bg]} style={styles.screen}>
      <Animated.View style={{ opacity: fade, alignItems: 'center' }}>
        <MonsterAvatar species={species} stage={stage} energy={petEnergy} size={130} />
        {params.evolvedTo && (
          <View style={styles.evoBanner}>
            <Text style={styles.evoText}>✨ EVOLVED INTO {params.evolvedTo.toUpperCase()} ✨</Text>
          </View>
        )}
      </Animated.View>

      <Animated.View style={{ transform: [{ scale }], alignItems: 'center' }}>
        <Text style={styles.big}>+{params.xp} XP</Text>
        <Text style={styles.dust}>+{params.dust} ✨ Dawn Dust</Text>
        {params.leveledUp && <Text style={styles.levelUp}>⬆️ LEVEL UP!</Text>}
        {params.freezeUsed && <Text style={styles.freeze}>🧊 Streak Freeze saved your streak!</Text>}
        <View style={styles.streakBox}>
          <Text style={styles.streakNum}>🔥 {params.streak}</Text>
          <Text style={type.label}>day streak</Text>
        </View>
      </Animated.View>

      <Animated.View style={{ opacity: fade, width: '100%' }}>
        <Text style={[type.body, { textAlign: 'center', marginBottom: spacing.md, fontStyle: 'italic' }]}>
          {monsterName}: “{praise}”
        </Text>
        <NeonButton title="Claim & Continue" onPress={() => nav.reset({ index: 0, routes: [{ name: 'Tabs' }] })} />
        <NeonButton
          title="📣 Share this W"
          variant="ghost"
          style={{ marginTop: spacing.md }}
          onPress={() => {
            const evo = params.evolvedTo ? ` My monster just evolved into ${params.evolvedTo}!` : '';
            Share.share({
              message: `Day ${params.streak} 🔥 — woke up on time and ${monsterName} is thriving.${evo} Beat my streak. #WakeQuest`,
            }).catch(() => {});
          }}
        />
      </Animated.View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'space-around',
    padding: spacing.lg,
    paddingVertical: 72,
  },
  big: { fontSize: 64, fontWeight: '800', color: colors.cyan, letterSpacing: -1 },
  dust: { fontSize: 18, fontWeight: '700', color: colors.pink, marginTop: 2 },
  levelUp: { fontSize: 22, fontWeight: '800', color: colors.amber, marginTop: 6 },
  freeze: { fontSize: 15, fontWeight: '700', color: colors.cyan, marginTop: 6 },
  streakBox: { alignItems: 'center', marginTop: spacing.lg },
  streakNum: { fontSize: 40, fontWeight: '700', color: colors.amber },
  evoBanner: {
    marginTop: spacing.md,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 999,
    backgroundColor: 'rgba(251,191,36,0.14)',
    borderWidth: 1,
    borderColor: 'rgba(251,191,36,0.45)',
  },
  evoText: { color: colors.amber, fontWeight: '800', letterSpacing: 1 },
});
