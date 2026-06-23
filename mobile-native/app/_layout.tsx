import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { colors } from "@/theme";
import "@/i18n"; // i18n 초기화

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.primary },
          headerTintColor: "#fff",
          headerTitleStyle: { fontWeight: "700" },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="index" options={{ title: "BADA" }} />
        <Stack.Screen name="login" options={{ title: "로그인" }} />
        <Stack.Screen name="cases/index" options={{ title: "내 사건" }} />
        <Stack.Screen name="cases/[id]" options={{ title: "사건 상세" }} />
        <Stack.Screen name="gps" options={{ title: "GPS 근무 증거" }} />
      </Stack>
    </SafeAreaProvider>
  );
}
