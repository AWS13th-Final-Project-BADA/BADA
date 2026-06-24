import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  Alert,
  TextInput,
} from "react-native";
import { useRouter } from "expo-router";
import { login, setTokenManually } from "@/lib/auth";
import { t } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

export default function Login() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [devToken, setDevToken] = useState("");

  async function doLogin(provider: "cognito" | "kakao" | "google" | "naver") {
    setBusy(true);
    try {
      const ok = await login(provider);
      if (ok) router.replace("/");
      else Alert.alert("로그인 실패", "토큰을 받지 못했습니다. 다시 시도해 주세요.");
    } catch (e: any) {
      Alert.alert("로그인 오류", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t("common.appName")}</Text>
      <Text style={styles.sub}>{t("common.tagline")}</Text>

      {busy && <ActivityIndicator color={colors.primary} />}

      <Pressable style={styles.btn} onPress={() => doLogin("cognito")}>
        <Text style={styles.btnText}>이메일 로그인 (Cognito)</Text>
      </Pressable>
      <Pressable
        style={[styles.btn, styles.kakao]}
        onPress={() => doLogin("kakao")}
      >
        <Text style={styles.btnText}>카카오로 로그인</Text>
      </Pressable>
      <Pressable
        style={[styles.btn, styles.google]}
        onPress={() => doLogin("google")}
      >
        <Text style={[styles.btnText, { color: colors.text }]}>
          구글로 로그인
        </Text>
      </Pressable>

      {/* 백엔드 딥링크 연계 전 임시: 데모 토큰 수동 주입(계획서 §6) */}
      <View style={styles.devBox}>
        <Text style={styles.devLabel}>개발용 토큰 주입(임시)</Text>
        <TextInput
          style={styles.input}
          placeholder="access_token 붙여넣기"
          autoCapitalize="none"
          value={devToken}
          onChangeText={setDevToken}
        />
        <Pressable
          style={styles.devBtn}
          onPress={async () => {
            if (!devToken.trim()) return;
            await setTokenManually(devToken.trim());
            router.replace("/");
          }}
        >
          <Text style={styles.devBtnText}>토큰으로 입장</Text>
        </Pressable>
      </View>

      <Text style={styles.disclaimer}>{t("disclaimer")}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, gap: spacing.sm },
  title: { fontSize: 32, fontWeight: "800", color: colors.primary },
  sub: { color: colors.textMuted, marginBottom: spacing.lg },
  btn: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
  },
  kakao: { backgroundColor: "#FEE500" },
  google: { backgroundColor: "#fff", borderWidth: 1, borderColor: colors.border },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  devBox: {
    marginTop: spacing.xl,
    padding: spacing.md,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: colors.border,
    borderRadius: radius.md,
    gap: spacing.sm,
  },
  devLabel: { fontSize: 12, color: colors.textMuted },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: spacing.sm,
    backgroundColor: "#fff",
  },
  devBtn: {
    backgroundColor: colors.text,
    borderRadius: radius.sm,
    padding: spacing.sm,
    alignItems: "center",
  },
  devBtnText: { color: "#fff", fontWeight: "600" },
  disclaimer: {
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
    marginTop: "auto",
  },
});
