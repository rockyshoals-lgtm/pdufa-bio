import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { glow } from '../theme/theme';
import { MOOD_META, moodFromEnergy } from '../logic/pet';

const FACES: Record<string, string> = {
  radiant: '(≧▽≦)',
  happy: '(＾◡＾)',
  sleepy: '(－ω－) zZ',
  sad: '(´•̥ ω •̥`)',
  sick: '(×﹏×)',
};

export function PetAvatar({ energy, size = 160 }: { energy: number; size?: number }) {
  const mood = moodFromEnergy(energy);
  const meta = MOOD_META[mood];
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

  return (
    <View style={styles.center}>
      <Animated.View style={[glow(meta.color, 30), { transform: [{ translateY }, { scale: pulse }] }]}>
        <LinearGradient
          colors={[meta.color, '#8B5CF6']}
          start={{ x: 0.2, y: 0 }}
          end={{ x: 0.9, y: 1 }}
          style={[styles.blob, { width: size, height: size, borderRadius: size / 2 }]}
        >
          <Text style={[styles.face, { fontSize: size / 7 }]}>{FACES[mood]}</Text>
        </LinearGradient>
      </Animated.View>
      <Text style={styles.moodEmoji}>{meta.emoji}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center' },
  blob: { alignItems: 'center', justifyContent: 'center' },
  face: { color: 'rgba(7,11,20,0.85)', fontWeight: '700' },
  moodEmoji: { fontSize: 28, marginTop: 12 },
});
