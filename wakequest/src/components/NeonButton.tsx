import React from 'react';
import { Pressable, StyleSheet, Text, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { colors, glow, radius } from '../theme/theme';

interface Props {
  title: string;
  onPress: () => void;
  colors?: readonly [string, string];
  variant?: 'solid' | 'ghost';
  style?: ViewStyle;
  disabled?: boolean;
}

export function NeonButton({
  title,
  onPress,
  colors: grad = [colors.violet, colors.cyan],
  variant = 'solid',
  style,
  disabled,
}: Props) {
  const handlePress = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    onPress();
  };

  if (variant === 'ghost') {
    return (
      <Pressable
        onPress={handlePress}
        disabled={disabled}
        style={({ pressed }) => [styles.ghost, style, pressed && { opacity: 0.6 }, disabled && { opacity: 0.35 }]}
      >
        <Text style={styles.ghostText}>{title}</Text>
      </Pressable>
    );
  }

  return (
    <Pressable
      onPress={handlePress}
      disabled={disabled}
      style={({ pressed }) => [
        glow(grad[0]),
        style,
        pressed && { transform: [{ scale: 0.97 }] },
        disabled && { opacity: 0.35 },
      ]}
    >
      <LinearGradient colors={[...grad]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.solid}>
        <Text style={styles.solidText}>{title}</Text>
      </LinearGradient>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  solid: {
    paddingVertical: 16,
    paddingHorizontal: 28,
    borderRadius: radius.pill,
    alignItems: 'center',
  },
  solidText: { color: '#fff', fontSize: 16, fontWeight: '700', letterSpacing: 0.4 },
  ghost: {
    paddingVertical: 15,
    paddingHorizontal: 28,
    borderRadius: radius.pill,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.glassBright,
    backgroundColor: colors.glass,
  },
  ghostText: { color: colors.textDim, fontSize: 15, fontWeight: '600' },
});
