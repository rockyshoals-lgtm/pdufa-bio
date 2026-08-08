import React, { useEffect, useRef } from 'react';
import { AppState, Text } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { DarkTheme, NavigationContainer, NavigationContainerRef } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import * as Notifications from 'expo-notifications';
import { colors } from './src/theme/theme';
import { setupAndroidChannel } from './src/logic/alarms';
import { getNativeLaunchAlarmId } from './src/logic/nativeAlarm';
import { HomeScreen } from './src/screens/HomeScreen';
import { AddAlarmScreen } from './src/screens/AddAlarmScreen';
import { RingScreen } from './src/screens/RingScreen';
import { ChallengeScreen } from './src/screens/ChallengeScreen';
import { RewardScreen } from './src/screens/RewardScreen';
import { MonsterScreen } from './src/screens/PetScreen';
import { StarterScreen } from './src/screens/StarterScreen';
import { StatsScreen } from './src/screens/StatsScreen';
import { BattleSetupScreen } from './src/screens/BattleSetupScreen';
import { BattleScreen } from './src/screens/BattleScreen';
import { ShopScreen } from './src/screens/ShopScreen';
import { useStore } from './src/state/store';
import { RootStackParamList } from './src/types';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

const theme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: colors.bg,
    card: colors.bgElevated,
    text: colors.text,
    primary: colors.cyan,
    border: 'rgba(255,255,255,0.06)',
  },
};

function Tabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: 'rgba(12,18,32,0.96)',
          borderTopColor: 'rgba(255,255,255,0.06)',
          height: 84,
          paddingTop: 8,
        },
        tabBarActiveTintColor: colors.cyan,
        tabBarInactiveTintColor: colors.textFaint,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        tabBarIcon: ({ focused }) => {
          const icons: Record<string, string> = { Alarms: '⏰', Monster: '👾', Stats: '📊' };
          return <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.45 }}>{icons[route.name]}</Text>;
        },
      })}
    >
      <Tab.Screen name="Alarms" component={HomeScreen} />
      <Tab.Screen name="Monster" component={MonsterScreen} />
      <Tab.Screen name="Stats" component={StatsScreen} />
    </Tab.Navigator>
  );
}

export default function App() {
  const navRef = useRef<NavigationContainerRef<RootStackParamList>>(null);
  const speciesId = useStore((s) => s.speciesId);

  useEffect(() => {
    setupAndroidChannel();

    // Alarm notification tapped → go straight to the ring screen
    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      const alarmId = response.notification.request.content.data?.alarmId as string | undefined;
      if (alarmId) navRef.current?.navigate('Ring', { alarmId });
    });

    // Launched from the native Android full-screen ring UI → straight to the challenge
    const nativeId = getNativeLaunchAlarmId();
    if (nativeId) {
      setTimeout(() => navRef.current?.navigate('Ring', { alarmId: nativeId }), 400);
    } else {
      // Cold start from a notification
      Notifications.getLastNotificationResponseAsync().then((response) => {
        const alarmId = response?.notification.request.content.data?.alarmId as string | undefined;
        if (alarmId) setTimeout(() => navRef.current?.navigate('Ring', { alarmId }), 400);
      });
    }

    // Warm start: app already running when the native ring UI hands off
    const appStateSub = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        const id = getNativeLaunchAlarmId();
        if (id) navRef.current?.navigate('Ring', { alarmId: id });
      }
    });

    return () => {
      sub.remove();
      appStateSub.remove();
    };
  }, []);

  // Onboarding gate: pick your starter monster before anything else
  if (!speciesId) {
    return (
      <>
        <StatusBar style="light" />
        <StarterScreen />
      </>
    );
  }

  return (
    <NavigationContainer ref={navRef} theme={theme}>
      <StatusBar style="light" />
      <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
        <Stack.Screen name="Tabs" component={Tabs} />
        <Stack.Screen name="AddAlarm" component={AddAlarmScreen} options={{ presentation: 'modal' }} />
        <Stack.Screen
          name="Ring"
          component={RingScreen}
          options={{ presentation: 'fullScreenModal', gestureEnabled: false }}
        />
        <Stack.Screen name="Challenge" component={ChallengeScreen} options={{ gestureEnabled: false }} />
        <Stack.Screen name="Reward" component={RewardScreen} options={{ gestureEnabled: false }} />
        <Stack.Screen name="BattleSetup" component={BattleSetupScreen} options={{ presentation: 'modal' }} />
        <Stack.Screen name="Battle" component={BattleScreen} options={{ gestureEnabled: false }} />
        <Stack.Screen name="Shop" component={ShopScreen} options={{ presentation: 'modal' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
