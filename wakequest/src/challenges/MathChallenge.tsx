import React, { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, radius, spacing, type } from '../theme/theme';

interface Problem {
  text: string;
  answer: number;
  options: number[];
}

function makeProblem(): Problem {
  const a = 10 + Math.floor(Math.random() * 40);
  const b = 10 + Math.floor(Math.random() * 40);
  const c = 2 + Math.floor(Math.random() * 8);
  const answer = a + b * c;
  const options = [answer, answer + c, answer - b, answer + 10]
    .map((v, i) => (i > 0 && v === answer ? v + 3 : v))
    .sort(() => Math.random() - 0.5);
  return { text: `${a} + ${b} × ${c}`, answer, options };
}

export function MathChallenge({ onDone }: { onDone: (perfect: boolean) => void }) {
  const problems = useMemo(() => [makeProblem(), makeProblem(), makeProblem()], []);
  const [index, setIndex] = useState(0);
  const [mistakes, setMistakes] = useState(0);

  const pick = (v: number) => {
    if (v === problems[index].answer) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      if (index === problems.length - 1) onDone(mistakes === 0);
      else setIndex(index + 1);
    } else {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
      setMistakes((m) => m + 1);
    }
  };

  return (
    <View style={styles.wrap}>
      <Text style={type.label}>
        Problem {index + 1} / {problems.length}
      </Text>
      <Text style={styles.problem}>{problems[index].text} = ?</Text>
      <View style={styles.grid}>
        {problems[index].options.map((o, i) => (
          <Pressable key={`${index}-${i}`} onPress={() => pick(o)} style={styles.option}>
            <Text style={styles.optionText}>{o}</Text>
          </Pressable>
        ))}
      </View>
      {mistakes > 0 && <Text style={styles.miss}>✗ {mistakes} wrong — no perfect bonus</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', width: '100%' },
  problem: { fontSize: 44, fontWeight: '300', color: colors.text, marginVertical: spacing.xl, letterSpacing: 1 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, justifyContent: 'center' },
  option: {
    width: '45%',
    paddingVertical: 22,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderWidth: 1,
    borderColor: colors.glassBorder,
    alignItems: 'center',
  },
  optionText: { fontSize: 24, fontWeight: '600', color: colors.cyan },
  miss: { color: colors.red, marginTop: spacing.lg, fontWeight: '600' },
});
