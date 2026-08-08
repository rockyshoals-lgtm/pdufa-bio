import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { useStore } from '../state/store';
import { MonsterAvatar } from '../components/MonsterAvatar';
import { NeonButton } from '../components/NeonButton';
import { GlassCard } from '../components/GlassCard';
import { colors, radius, spacing, type } from '../theme/theme';
import { MAX_STAGE, SPECIES } from '../logic/monsters';

export function StarterScreen() {
  const chooseStarter = useStore((s) => s.chooseStarter);
  const [selected, setSelected] = useState<string | null>(null);
  const pick = SPECIES.find((s) => s.id === selected);

  return (
    <LinearGradient colors={['#141033', colors.bg]} style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={type.label}>WAKEQUEST</Text>
        <Text style={[type.h1, { marginTop: 6 }]}>Choose your monster</Text>
        <Text style={[type.body, { marginTop: 6, marginBottom: spacing.lg }]}>
          It evolves {MAX_STAGE} times — powered entirely by you waking up. Choose wisely. It talks back.
        </Text>

        <View style={styles.grid}>
          {SPECIES.map((s) => (
            <Pressable
              key={s.id}
              onPress={() => {
                Haptics.selectionAsync().catch(() => {});
                setSelected(s.id);
              }}
              style={[styles.card, selected === s.id && { borderColor: s.colors[0], borderWidth: 2 }]}
            >
              <MonsterAvatar species={s} stage={0} energy={70} size={80} />
              <Text style={[type.h2, { marginTop: 12 }]}>{s.name}</Text>
              <Text style={[styles.vibe]}>{s.vibe}</Text>
            </Pressable>
          ))}
        </View>

        {pick && (
          <GlassCard style={{ marginTop: spacing.lg }}>
            <Text style={[type.label, { marginBottom: 6 }]}>{pick.name} says</Text>
            <Text style={[type.body, { fontStyle: 'italic' }]}>“{pick.dialogue.greeting[0]}”</Text>
            <Text style={[type.body, { marginTop: 10 }]}>{pick.bio}</Text>
          </GlassCard>
        )}

        <NeonButton
          title={pick ? `Begin with ${pick.name}` : 'Pick a monster'}
          disabled={!pick}
          onPress={() => selected && chooseStarter(selected)}
          colors={pick ? pick.colors : undefined}
          style={{ marginTop: spacing.lg, marginBottom: spacing.xl }}
        />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  scroll: { padding: spacing.lg, paddingTop: 84 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  card: {
    flexBasis: '47%',
    flexGrow: 1,
    alignItems: 'center',
    padding: spacing.md,
    paddingVertical: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  vibe: { ...type.body, fontSize: 12, textAlign: 'center', marginTop: 6, lineHeight: 17 },
});
