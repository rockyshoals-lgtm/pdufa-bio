import React, { useEffect, useRef, useState } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
import { Accelerometer } from 'expo-sensors';
import * as Haptics from 'expo-haptics';
import { colors, spacing, type } from '../theme/theme';

const TARGET = 30;
const THRESHOLD = 1.9; // total g-force to count as a shake

export function ShakeChallenge({ onDone }: { onDone: (perfect: boolean) => void }) {
  const [count, setCount] = useState(0);
  const startTime = useRef(Date.now());
  const lastShake = useRef(0);
  const scale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Accelerometer.setUpdateInterval(60);
    const sub = Accelerometer.addListener(({ x, y, z }) => {
      const force = Math.sqrt(x * x + y * y + z * z);
      const now = Date.now();
      if (force > THRESHOLD && now - lastShake.current > 180) {
        lastShake.current = now;
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
        Animated.sequence([
          Animated.timing(scale, { toValue: 1.25, duration: 80, useNativeDriver: true }),
          Animated.timing(scale, { toValue: 1, duration: 120, useNativeDriver: true }),
        ]).start();
        setCount((c) => c + 1);
      }
    });
    return () => sub.remove();
  }, [scale]);

  useEffect(() => {
    if (count >= TARGET) {
      const elapsed = (Date.now() - startTime.current) / 1000;
      onDone(elapsed < 20); // perfect if done in under 20s
    }
  }, [count]); // eslint-disable-line react-hooks/exhaustive-deps

  const pct = Math.min(1, count / TARGET);

  return (
    <View style={styles.wrap}>
      <Text style={type.label}>Shake your phone awake</Text>
      <Animated.Text style={[styles.count, { transform: [{ scale }] }]}>{count}</Animated.Text>
      <Text style={type.body}>of {TARGET} shakes</Text>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${pct * 100}%` }]} />
      </View>
      <Text style={[type.body, { marginTop: spacing.lg }]}>📳 Under 20 seconds = perfect bonus</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', width: '100%' },
  count: { fontSize: 96, fontWeight: '200', color: colors.pink, marginVertical: spacing.md, letterSpacing: -3 },
  track: {
    height: 12,
    width: '90%',
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.07)',
    overflow: 'hidden',
    marginTop: spacing.lg,
  },
  fill: { height: '100%', backgroundColor: colors.pink, borderRadius: 999 },
});
