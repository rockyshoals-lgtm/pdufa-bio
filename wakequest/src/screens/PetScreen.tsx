import React, { useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useStore } from '../state/store';
import { GlassCard } from '../components/GlassCard';
import { MonsterAvatar } from '../components/MonsterAvatar';
import { NeonButton } from '../components/NeonButton';
import { colors, radius, spacing, type } from '../theme/theme';
import { moodFromEnergy } from '../logic/pet';
import { getCosmetic } from '../logic/economy';
import { dailyLine, evolutionProgress, getSpecies, MAX_STAGE } from '../logic/monsters';
import { RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function MonsterScreen() {
  const nav = useNavigation<Nav>();
  const { petEnergy, petName, renamePet, speciesId, wakePower, dawnDust, equippedHat, equippedAura } = useStore();
  const [editing, setEditing] = useState(false);
  const species = getSpecies(speciesId);
  const { stage, pct, into, needed, maxed } = evolutionProgress(wakePower);
  const form = species.forms[stage];
  const mood = moodFromEnergy(petEnergy);
  const displayName = petName || species.name;
  const [name, setName] = useState(displayName);

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.scroll}>
      {editing ? (
        <TextInput
          value={name}
          onChangeText={setName}
          onBlur={() => {
            renamePet(name);
            setEditing(false);
          }}
          autoFocus
          style={styles.nameInput}
        />
      ) : (
        <Text style={type.h1} onPress={() => setEditing(true)}>
          {displayName} ✏️
        </Text>
      )}
      <Text style={[type.label, { marginTop: 4 }]}>
        Stage {stage}/{MAX_STAGE} · {form.name}
      </Text>

      <View style={{ marginVertical: spacing.xl }}>
        <MonsterAvatar
          species={species}
          stage={stage}
          energy={petEnergy}
          hatEmoji={getCosmetic(equippedHat)?.emoji}
          auraColor={getCosmetic(equippedAura)?.color}
        />
      </View>

      <View style={styles.actions}>
        <NeonButton title="⚔️ Battle" onPress={() => nav.navigate('BattleSetup')} style={{ flex: 1 }} />
        <NeonButton title={`✨ ${dawnDust} · Shop`} variant="ghost" onPress={() => nav.navigate('Shop')} style={{ flex: 1 }} />
      </View>

      <GlassCard style={{ width: '100%', marginBottom: spacing.md }}>
        <Text style={[type.label, { marginBottom: 6 }]}>{displayName} says</Text>
        <Text style={[type.body, { fontStyle: 'italic' }]}>“{species.dialogue.moods[mood]}”</Text>
        <Text style={[type.body, { marginTop: 8, fontStyle: 'italic', color: colors.textFaint }]}>
          “{dailyLine(species.dialogue.greeting)}”
        </Text>
      </GlassCard>

      <GlassCard style={{ width: '100%', marginBottom: spacing.md }}>
        <Text style={[type.label, { marginBottom: 8 }]}>
          {maxed ? 'FINAL FORM REACHED' : `Next evolution: ${species.forms[stage + 1].name}`}
        </Text>
        <View style={styles.track}>
          <View style={[styles.fill, { width: `${Math.round(pct * 100)}%`, backgroundColor: species.colors[0] }]} />
        </View>
        <Text style={[type.body, { marginTop: 10 }]}>
          {maxed
            ? `${displayName} has ascended. ${wakePower} wake power collected.`
            : `${into}/${needed} wake power · on-time wake +2, snoozed wake +1`}
        </Text>
      </GlassCard>

      <GlassCard style={{ width: '100%', marginBottom: spacing.md }}>
        <Text style={[type.label, { marginBottom: 10 }]}>Evolution line</Text>
        {species.forms.map((f, i) => {
          const unlocked = i <= stage;
          return (
            <View key={f.name} style={styles.formRow}>
              <Text style={{ fontSize: 18, opacity: unlocked ? 1 : 0.25 }}>{unlocked ? f.emoji : '🔒'}</Text>
              <Text
                style={[
                  type.body,
                  unlocked && { color: colors.text },
                  i === stage && { color: species.colors[0], fontWeight: '700' },
                ]}
              >
                {unlocked ? f.name : '???'}
              </Text>
              {i === stage && <Text style={[type.label, { color: species.colors[0] }]}>NOW</Text>}
            </View>
          );
        })}
      </GlassCard>

      <GlassCard style={{ width: '100%' }}>
        <Text style={[type.label, { marginBottom: 8 }]}>Energy</Text>
        <View style={styles.track}>
          <View style={[styles.fill, { width: `${petEnergy}%`, backgroundColor: colors.green }]} />
        </View>
        <Text style={[type.body, { marginTop: 10 }]}>
          On-time wake +18 · snooze −12. Energy drives mood, wake power drives evolution.
        </Text>
      </GlassCard>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  scroll: { alignItems: 'center', padding: spacing.lg, paddingTop: 64, paddingBottom: 48 },
  nameInput: {
    ...type.h1,
    borderBottomWidth: 1,
    borderColor: colors.cyan,
    paddingBottom: 4,
    minWidth: 160,
    textAlign: 'center',
  },
  actions: { flexDirection: 'row', gap: 12, width: '100%', marginBottom: spacing.md },
  track: { height: 12, borderRadius: radius.pill, backgroundColor: 'rgba(255,255,255,0.07)', overflow: 'hidden' },
  fill: { height: '100%', borderRadius: radius.pill },
  formRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 6 },
});
