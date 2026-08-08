import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, radius, spacing, type } from '../theme/theme';

const EMOJIS = ['🌞', '🌙', '⭐', '🔥', '⚡', '🌈'];

interface Card {
  id: number;
  emoji: string;
  matched: boolean;
}

function shuffle<T>(arr: T[]): T[] {
  return [...arr].sort(() => Math.random() - 0.5);
}

export function MemoryChallenge({ onDone }: { onDone: (perfect: boolean) => void }) {
  const [cards] = useState<Card[]>(() =>
    shuffle(EMOJIS.flatMap((e, i) => [
      { id: i * 2, emoji: e, matched: false },
      { id: i * 2 + 1, emoji: e, matched: false },
    ]))
  );
  const [matched, setMatched] = useState<Set<string>>(new Set());
  const [flipped, setFlipped] = useState<number[]>([]);
  const [misses, setMisses] = useState(0);

  useEffect(() => {
    if (flipped.length === 2) {
      const [a, b] = flipped;
      if (cards[a].emoji === cards[b].emoji) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
        const next = new Set(matched);
        next.add(cards[a].emoji);
        setMatched(next);
        setFlipped([]);
        if (next.size === EMOJIS.length) {
          setTimeout(() => onDone(misses <= 3), 400);
        }
      } else {
        setMisses((m) => m + 1);
        const t = setTimeout(() => setFlipped([]), 650);
        return () => clearTimeout(t);
      }
    }
  }, [flipped]); // eslint-disable-line react-hooks/exhaustive-deps

  const tap = (i: number) => {
    if (flipped.length >= 2 || flipped.includes(i) || matched.has(cards[i].emoji)) return;
    Haptics.selectionAsync().catch(() => {});
    setFlipped((f) => [...f, i]);
  };

  return (
    <View style={styles.wrap}>
      <Text style={type.label}>Match all pairs ({matched.size}/{EMOJIS.length})</Text>
      <View style={styles.grid}>
        {cards.map((c, i) => {
          const up = flipped.includes(i) || matched.has(c.emoji);
          return (
            <Pressable key={c.id} onPress={() => tap(i)} style={[styles.card, up && styles.cardUp]}>
              <Text style={styles.emoji}>{up ? c.emoji : '?'}</Text>
            </Pressable>
          );
        })}
      </View>
      <Text style={[type.body, { marginTop: spacing.md }]}>
        Misses: {misses} {misses <= 3 ? '(perfect bonus still live!)' : ''}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', width: '100%' },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    justifyContent: 'center',
    marginTop: spacing.lg,
    maxWidth: 320,
  },
  card: {
    width: 68,
    height: 68,
    borderRadius: radius.sm,
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderWidth: 1,
    borderColor: colors.glassBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardUp: { backgroundColor: 'rgba(139,92,246,0.30)', borderColor: colors.violet },
  emoji: { fontSize: 28, color: colors.textDim },
});
