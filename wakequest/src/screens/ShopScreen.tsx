import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import * as Haptics from 'expo-haptics';
import { useStore } from '../state/store';
import { GlassCard } from '../components/GlassCard';
import { NeonButton } from '../components/NeonButton';
import { colors, radius, spacing, type } from '../theme/theme';
import { COSMETICS, MAX_STREAK_FREEZES, STREAK_FREEZE_COST } from '../logic/economy';
import { RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function ShopScreen() {
  const nav = useNavigation<Nav>();
  const { dawnDust, ownedCosmetics, equippedHat, equippedAura, streakFreezes, buyCosmetic, equipCosmetic, buyStreakFreeze } =
    useStore();

  const handleItem = (id: string, slot: 'hat' | 'aura') => {
    const owned = ownedCosmetics.includes(id);
    const equipped = slot === 'hat' ? equippedHat === id : equippedAura === id;
    if (!owned) {
      if (buyCosmetic(id)) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
        equipCosmetic(id, slot);
      } else {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
      }
    } else {
      equipCosmetic(equipped ? null : id, slot);
      Haptics.selectionAsync().catch(() => {});
    }
  };

  const hats = COSMETICS.filter((c) => c.slot === 'hat');
  const auras = COSMETICS.filter((c) => c.slot === 'aura');

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ padding: spacing.lg, paddingTop: 72, paddingBottom: 48 }}>
      <View style={styles.header}>
        <Text style={type.h1}>Dust Shop</Text>
        <View style={styles.dustPill}>
          <Text style={styles.dustText}>✨ {dawnDust}</Text>
        </View>
      </View>
      <Text style={[type.body, { marginBottom: spacing.lg }]}>
        Dawn Dust is earned only by waking up. Everything here is cosmetic — no shortcuts for sale.
      </Text>

      <GlassCard style={{ marginBottom: spacing.md }}>
        <View style={styles.freezeRow}>
          <View style={{ flex: 1 }}>
            <Text style={type.h2}>🧊 Streak Freeze</Text>
            <Text style={[type.body, { marginTop: 4 }]}>
              Auto-saves your streak if you miss a day. Banked: {streakFreezes}/{MAX_STREAK_FREEZES}
            </Text>
          </View>
          <NeonButton
            title={`${STREAK_FREEZE_COST} ✨`}
            variant="ghost"
            disabled={streakFreezes >= MAX_STREAK_FREEZES || dawnDust < STREAK_FREEZE_COST}
            onPress={() => {
              if (buyStreakFreeze()) Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
            }}
          />
        </View>
      </GlassCard>

      {[
        { title: 'Hats', items: hats, slot: 'hat' as const, equippedId: equippedHat },
        { title: 'Auras', items: auras, slot: 'aura' as const, equippedId: equippedAura },
      ].map((section) => (
        <View key={section.title}>
          <Text style={[type.label, { marginVertical: spacing.sm }]}>{section.title}</Text>
          <View style={styles.grid}>
            {section.items.map((c) => {
              const owned = ownedCosmetics.includes(c.id);
              const equipped = section.equippedId === c.id;
              const affordable = dawnDust >= c.cost;
              return (
                <Pressable
                  key={c.id}
                  onPress={() => handleItem(c.id, section.slot)}
                  style={[
                    styles.item,
                    equipped && { borderColor: c.color ?? colors.cyan, borderWidth: 2 },
                    !owned && !affordable && { opacity: 0.45 },
                  ]}
                >
                  <Text style={{ fontSize: 30 }}>{c.emoji}</Text>
                  <Text style={styles.itemName}>{c.name}</Text>
                  <Text style={[styles.itemCost, owned && { color: colors.green }]}>
                    {equipped ? 'EQUIPPED' : owned ? 'Tap to equip' : `${c.cost} ✨`}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      ))}

      <NeonButton title="Back" variant="ghost" onPress={() => nav.goBack()} style={{ marginTop: spacing.lg }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  dustPill: {
    backgroundColor: 'rgba(34,211,238,0.10)',
    borderColor: 'rgba(34,211,238,0.35)',
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  dustText: { color: colors.cyan, fontWeight: '700', fontSize: 15 },
  freezeRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  item: {
    flexBasis: '30%',
    flexGrow: 1,
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 8,
    borderRadius: radius.md,
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  itemName: { color: colors.text, fontSize: 12, fontWeight: '600', marginTop: 8, textAlign: 'center' },
  itemCost: { color: colors.textDim, fontSize: 11, marginTop: 4, fontWeight: '600' },
});
