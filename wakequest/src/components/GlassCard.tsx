import React from 'react';
import { StyleSheet, View, ViewProps } from 'react-native';
import { BlurView } from 'expo-blur';
import { colors, radius } from '../theme/theme';

interface Props extends ViewProps {
  padding?: number;
}

export function GlassCard({ children, style, padding = 18, ...rest }: Props) {
  return (
    <View style={[styles.wrap, style]} {...rest}>
      <BlurView intensity={28} tint="dark" style={StyleSheet.absoluteFill} />
      <View style={[styles.inner, { padding }]}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: radius.lg,
    overflow: 'hidden',
    backgroundColor: colors.glass,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.glassBorder,
  },
  inner: {},
});
