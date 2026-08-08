import React, { useMemo, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { colors, radius, spacing, type } from '../theme/theme';

const PHRASES = [
  'I am awake and unstoppable today',
  'the early bird gets the alpha',
  'no snooze can hold me down',
  'discipline is my superpower',
  'today I move before the market does',
  'my streak is worth more than sleep',
];

export function TypingChallenge({ onDone }: { onDone: (perfect: boolean) => void }) {
  const phrase = useMemo(() => PHRASES[Math.floor(Math.random() * PHRASES.length)], []);
  const [text, setText] = useState('');
  const [errors, setErrors] = useState(0);

  const handleChange = (t: string) => {
    if (!phrase.startsWith(t) && t.length > text.length) setErrors((e) => e + 1);
    setText(t);
    if (t === phrase) onDone(errors === 0);
  };

  const chars = phrase.split('');

  return (
    <View style={styles.wrap}>
      <Text style={type.label}>Type this to prove you're awake</Text>
      <Text style={styles.phrase}>
        {chars.map((c, i) => {
          let color = colors.textFaint;
          if (i < text.length) color = text[i] === c ? colors.green : colors.red;
          return (
            <Text key={i} style={{ color }}>
              {c}
            </Text>
          );
        })}
      </Text>
      <TextInput
        value={text}
        onChangeText={handleChange}
        autoFocus
        autoCorrect={false}
        autoCapitalize="none"
        style={styles.input}
        placeholder="start typing…"
        placeholderTextColor={colors.textFaint}
      />
      <Text style={[type.body, { marginTop: spacing.md }]}>
        {errors === 0 ? '✨ Flawless so far — perfect bonus live' : `Typos: ${errors}`}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', width: '100%' },
  phrase: {
    fontSize: 22,
    lineHeight: 34,
    fontWeight: '500',
    textAlign: 'center',
    marginVertical: spacing.xl,
    paddingHorizontal: spacing.md,
  },
  input: {
    width: '100%',
    color: colors.text,
    fontSize: 18,
    padding: 16,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
});
