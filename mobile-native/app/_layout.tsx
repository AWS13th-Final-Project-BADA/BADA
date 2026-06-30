import { useCallback, useState } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import "@/i18n"; // i18n 초기화
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
          <Stack.Screen name="login" options={{ title: "로그인" }} />
          <Stack.Screen name="cases/index" options={{ title: "내 사건" }} />
          <Stack.Screen name="cases/new" options={{ title: "새 사건 만들기" }} />
          <Stack.Screen name="cases/[id]" options={{ title: "사건 상세" }} />
          <Stack.Screen name="cases/upload" options={{ title: "증거 업로드" }} />
          <Stack.Screen name="cases/analysis" options={{ title: "분석 결과" }} />
          <Stack.Screen name="community/index" options={{ title: "커뮤니티" }} />
          <Stack.Screen name="community/new" options={{ title: "글쓰기" }} />
          <Stack.Screen name="community/[id]" options={{ title: "게시글" }} />
          <Stack.Screen name="chat" options={{ title: "AI 상담" }} />
          <Stack.Screen name="gps" options={{ title: "GPS 근무 증거" }} />
          <Stack.Screen name="settings" options={{ title: "설정" }} />
          <Stack.Screen name="notifications" options={{ title: "알림" }} />
        </Stack>
        {showSplash ? <AppSplash onFinish={finishSplash} /> : null}
      </LocaleProvider>
    </SafeAreaProvider>
  );
}
