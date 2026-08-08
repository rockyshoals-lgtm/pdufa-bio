import React, { useMemo, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { CameraView, useCameraPermissions } from 'expo-camera';
import QRCode from 'react-native-qrcode-svg';
import * as Haptics from 'expo-haptics';
import { useStore } from '../state/store';
import { GlassCard } from '../components/GlassCard';
import { NeonButton } from '../components/NeonButton';
import { colors, radius, spacing, type } from '../theme/theme';
import { encodeBattlePayload, decodeBattlePayload } from '../logic/battle';
import { getSpecies, stageForPower } from '../logic/monsters';
import { RootStackParamList } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function BattleSetupScreen() {
  const nav = useNavigation<Nav>();
  const { petName, speciesId, wakePower, streak, petEnergy, history } = useStore();
  const [mode, setMode] = useState<'show' | 'scan'>('show');
  const [permission, requestPermission] = useCameraPermissions();
  const scanned = useRef(false);

  const species = getSpecies(speciesId);
  const stage = stageForPower(wakePower);
  const onTimeRate = history.length > 0 ? history.filter((h) => h.onTime).length / history.length : 0.5;

  const myPayload = useMemo(
    () =>
      encodeBattlePayload({
        name: petName || species.name,
        speciesId: species.id,
        stage,
        streak,
        onTimeRate,
        energy: petEnergy,
        seed: Math.floor(Math.random() * 2 ** 31),
      }),
    [petName, species, stage, streak, onTimeRate, petEnergy]
  );

  const onScan = ({ data }: { data: string }) => {
    if (scanned.current) return;
    const opponent = decodeBattlePayload(data);
    if (!opponent) return;
    scanned.current = true;
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    nav.replace('Battle', { me: myPayload, opponent: data });
  };

  return (
    <View style={styles.screen}>
      <Text style={[type.h1, { marginBottom: 4 }]}>⚔️ Monster Battle</Text>
      <Text style={[type.body, { marginBottom: spacing.lg }]}>
        Face a friend. One of you shows a code, the other scans. Wake stats decide who hits harder.
      </Text>

      <View style={styles.toggle}>
        <NeonButton
          title="My Code"
          variant={mode === 'show' ? 'solid' : 'ghost'}
          onPress={() => setMode('show')}
          style={{ flex: 1 }}
        />
        <NeonButton
          title="Scan Friend"
          variant={mode === 'scan' ? 'solid' : 'ghost'}
          onPress={async () => {
            if (!permission?.granted) {
              const r = await requestPermission();
              if (!r.granted) return;
            }
            setMode('scan');
          }}
          style={{ flex: 1 }}
        />
      </View>

      {mode === 'show' ? (
        <GlassCard style={{ alignItems: 'center', marginTop: spacing.lg }} padding={28}>
          <View style={styles.qrBox}>
            <QRCode value={myPayload} size={220} backgroundColor="#FFFFFF" color="#070B14" />
          </View>
          <Text style={[type.h2, { marginTop: spacing.md }]}>
            {petName || species.name} · Stage {stage}
          </Text>
          <Text style={type.body}>
            🔥 {streak} streak · {Math.round(onTimeRate * 100)}% on-time · {petEnergy} energy
          </Text>
        </GlassCard>
      ) : (
        <GlassCard style={{ marginTop: spacing.lg, overflow: 'hidden' }} padding={0}>
          {permission?.granted ? (
            <CameraView
              style={styles.camera}
              barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
              onBarcodeScanned={onScan}
            />
          ) : (
            <Text style={[type.body, { padding: spacing.lg, textAlign: 'center' }]}>
              Camera permission needed to scan your friend's Battle Code.
            </Text>
          )}
        </GlassCard>
      )}

      <NeonButton title="Back" variant="ghost" onPress={() => nav.goBack()} style={{ marginTop: spacing.lg }} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg, padding: spacing.lg, paddingTop: 72 },
  toggle: { flexDirection: 'row', gap: 12 },
  qrBox: { backgroundColor: '#FFFFFF', padding: 14, borderRadius: radius.md },
  camera: { width: '100%', height: 320 },
});
