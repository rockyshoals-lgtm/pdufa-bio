import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients, radius, type } from '../theme/theme';
import { levelProgress, titleForLevel } from '../logic/xp';

export function XPBar({ xp }: { xp: number }) {
  const { level, pct, into, needed } = levelProgress(xp);
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.spring(anim, { toValue: pct, useNativeDriver: false, friction: 8 }).start();
  }, [pct, anim]);

  return (
    <View>
      <View style={styles.row}>
        <Text style={styles.level}>
          LVL {level} <Text style={styles.title}>· {titleForLevel(level)}</Text>
        </Text>
        <Text style={styles.xp}>
          {into}/{needed} XP
        </Text>
      </View>
      <View style={styles.track}>
        <Animated.View
          style={{
            width: anim.interpolate({ inputRange: [0, 1], outputRange: ['2%', '100%'] }),
            height: '100%',
          }}
        >
          <LinearGradient
            colors={[...gradients.primary]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.fill}
          />
        </Animated.View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  level: { ...type.label, color: colors.cyan },
  title: { color: colors.textDim },
  xp: { ...type.label },
  track: {
    height: 10,
    borderRadius: radius.pill,
    backgroundColor: 'rgba(255,255,255,0.07)',
    overflow: 'hidden',
  },
  fill: { flex: 1, borderRadius: radius.pill },
});
