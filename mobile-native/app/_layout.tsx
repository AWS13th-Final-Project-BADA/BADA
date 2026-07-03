import { useCallback, useState } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { t } from "@/i18n"; // i18n 초기화
import { LocaleProvider } from "@/i18n/LocaleContext";
import { AppSplash } from "@/components/AppSplash";

export default function RootLayout() {
  const [showSplash, setShowSplash] = useState(true);
  const finishSplash = useCallback(() => setShowSplash(false), []);

  return (
    <SafeAreaProvider>
      <LocaleProvider>
        <StatusBar style="dark" backgroundColor="#FFFFFF" />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: "#f7f9fb" },
          }}
        >
          <Stack.Screen name="index" options={{ title: "BADA" }} />
          <Stack.Screen name="login" options={{ title: t("common.login") }} />
          <Stack.Screen name="cases/index" options={{ title: t("cases.title") }} />
          <Stack.Screen name="cases/new" options={{ title: t("cases.create") }} />
          <Stack.Screen name="cases/[id]" options={{ title: t("cases.detail") }} />
          <Stack.Screen name="cases/upload" options={{ title: t("upload.title") }} />
          <Stack.Screen name="cases/analysis" options={{ title: t("cases.analysis") }} />
          <Stack.Screen name="community/index" options={{ title: t("community.title") }} />
          <Stack.Screen name="community/new" options={{ title: t("community.write") }} />
          <Stack.Screen name="community/[id]" options={{ title: t("community.title") }} />
          <Stack.Screen name="chat" options={{ title: t("chat.title") }} />
          <Stack.Screen name="gps" options={{ title: t("gps.title") }} />
          <Stack.Screen name="settings" options={{ title: t("nav.settings") }} />
          <Stack.Screen name="notifications" options={{ title: t("nav.notifications") }} />
        </Stack>
        {showSplash ? <AppSplash onFinish={finishSplash} /> : null}
      </LocaleProvider>
    </SafeAreaProvider>
  );
}
