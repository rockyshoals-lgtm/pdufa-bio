import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { glow } from '../theme/theme';
import { moodFromEnergy } from '../logic/pet';
import { MonsterSpecies } from '../logic/monsters';

const FACES: Record<string, string> = {
  radiant: '(≧▽≦)',
  happy: '(＾◡＾)',
  sleepy: '(－ω－) zZ',
  sad: '(´•̥ ω •̥`)',
  sick: '(×﹏×)',
};

interface Props {
  species: MonsterSpecies;
  stage: number; // 0..10 — the monster grows and glows harder as it evolves
  energy: number;
  size?: number;
  hatEmoji?: string; // equipped cosmetic hat
  auraColor?: string; // equipped cosmetic aura (overrides glow color)
}

export function MonsterAvatar({ species, stage, energy, size, hatEmoji, auraColor }: Props) {
  const mood = moodFromEnergy(energy);
  const bodySize = size ?? 110 + stage * 7; // evolves bigger
  const glowRadius = (16 + stage * 3) * (auraColor ? 1.4 : 1); // evolves brighter; auras amplify
  const float = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(float, { toValue: 1, duration: 1800, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
        Animated.timing(float, { toValue: 0, duration: 1800, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      ])
    ).start();
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.05, duration: 1400, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 1400, useNativeDriver: true }),
      ])
    ).start();
  }, [float, pulse]);

  const translateY = float.interpolate({ inputRange: [0, 1], outputRange: [0, -10] });
  const form = species.forms[Math.min(stage, species.forms.length - 1)];

  return (
    <View style={styles.center}>
      <Animated.View
        style={[glow(auraColor ?? species.colors[0], glowRadius), { transform: [{ translateY }, { scale: pulse }] }]}
      >
        {hatEmoji && (
          <Text style={[styles.hat, { fontSize: bodySize / 3.4, top: -bodySize / 4.5 }]}>{hatEmoji}</Text>
        )}
        <LinearGradient
          colors={[...species.colors]}
          start={{ x: 0.2, y: 0 }}
          end={{ x: 0.9, y: 1 }}
          style={[styles.blob, { width: bodySize, height: bodySize, borderRadius: bodySize / 2 }]}
        >
          <Text style={[styles.face, { fontSize: bodySize / 7 }]}>{FACES[mood]}</Text>
        </LinearGradient>
        <View style={styles.badge}>
          <Text style={{ fontSize: 22 }}>{form.emoji}</Text>
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center' },
  blob: { alignItems: 'center', justifyContent: 'center' },
  face: { color: 'rgba(7,11,20,0.85)', fontWeight: '700' },
  hat: { position: 'absolute', alignSelf: 'center', zIndex: 2 },
  badge: {
    position: 'absolute',
    bottom: -4,
    right: -4,
    backgroundColor: 'rgba(12,18,32,0.92)',
    borderRadius: 20,
    padding: 5,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
  },
});
