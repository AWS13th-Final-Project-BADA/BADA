import { useState } from "react";
import { Alert, Image, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { login, setTokenManually, startDemoSession } from "@/lib/auth";
import { stitchImages } from "@/lib/stitchAssets";
import { Card, RemoteImage, StitchButton, StitchScreen, stitch } from "@/components/StitchKit";

export default function Login() {
  const router = useRouter();
  const [devToken, setDevToken] = useState("");
  const [busy, setBusy] = useState(false);

  async function doLogin(provider: "google" | "kakao" | "naver") {
    setBusy(true);
    try {
      const ok = await login(provider);
      if (ok) router.replace("/");
      else Alert.alert("로그인 실패", "토큰을 받지 못했어요. 개발 중에는 기능 먼저 둘러보기를 사용해 주세요.");
    } catch (e: any) {
      Alert.alert("로그인 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <StitchScreen bottom={false}>
      <View style={styles.header}>
        <Text style={styles.logo}>BADA</Text>
        <Pressable style={styles.lang}>
          <MaterialIcons name="translate" size={20} color={stitch.text} />
          <Text style={styles.langText}>한국어</Text>
          <MaterialIcons name="expand-more" size={22} color={stitch.text} />
        </Pressable>
      </View>

      <View style={styles.content}>
        <RemoteImage uri={stitchImages.loginSecurity} style={styles.securityImage} />

        <Text style={styles.title}>상담 전 자료를{"\n"}안전하게 정리하세요</Text>
        <Text style={styles.subtitle}>업로드한 자료와 분석 결과를 내 계정에 보관하고, 상담 준비 과정을 이어갈 수 있어요.</Text>

        <View style={styles.trustGrid}>
          <TrustCard icon="shield" title="자료 보호" />
          <TrustCard icon="gavel" title="법률 판단 없음" />
        </View>

        {__DEV__ ? (
          <StitchButton
            tone="blue"
            onPress={async () => {
              await startDemoSession();
              router.replace("/");
            }}
          >
            기능 먼저 둘러보기
          </StitchButton>
        ) : null}

        <Pressable style={styles.googleButton} onPress={() => doLogin("google")} disabled={busy}>
          <Image source={{ uri: stitchImages.google }} style={styles.googleIcon} />
          <Text style={styles.googleText}>구글로 시작하기</Text>
        </Pressable>
        <StitchButton tone="kakao" icon="chat-bubble-outline" onPress={() => doLogin("kakao")} disabled={busy}>
          <Text style={styles.kakaoText}>카카오로 시작하기</Text>
        </StitchButton>
        <StitchButton tone="naver" onPress={() => doLogin("naver")} disabled={busy}>
          <Text style={styles.naverText}>N  네이버로 시작하기</Text>
        </StitchButton>

        <Card style={styles.notice}>
          <MaterialIcons name="info-outline" size={22} color={stitch.outline} />
          <Text style={styles.noticeText}>
            BADA는 법률 판단을 하지 않습니다. AI가 생성한 결과는 상담 전 자료 정리를 돕기 위한 참고용입니다.
          </Text>
        </Card>

        <View style={styles.terms}>
          <Text style={styles.termText}>이용약관</Text>
          <Text style={styles.dot}>·</Text>
          <Text style={styles.termText}>개인정보처리방침</Text>
        </View>

        {__DEV__ ? (
          <View style={styles.devBox}>
            <TextInput
              style={styles.input}
              placeholder="access_token 붙여넣기"
              placeholderTextColor={stitch.outline}
              value={devToken}
              autoCapitalize="none"
              onChangeText={setDevToken}
            />
            <StitchButton
              tone="secondary"
              onPress={async () => {
                if (!devToken.trim()) return;
                await setTokenManually(devToken.trim());
                router.replace("/");
              }}
            >
              <Text style={styles.secondaryText}>토큰으로 입장</Text>
            </StitchButton>
          </View>
        ) : null}
      </View>
    </StitchScreen>
  );
}

function TrustCard({ icon, title }: { icon: keyof typeof MaterialIcons.glyphMap; title: string }) {
  return (
    <Card style={styles.trustCard}>
      <View style={styles.trustIcon}>
        <MaterialIcons name={icon} size={28} color={stitch.blue} />
      </View>
      <Text style={styles.trustTitle}>{title}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  header: {
    height: 92,
    paddingHorizontal: 32,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    borderBottomColor: "rgba(198,198,205,0.32)",
  },
  logo: { color: stitch.navy, fontSize: 34, lineHeight: 42, fontWeight: "900", letterSpacing: -0.6 },
  lang: { height: 46, borderRadius: 23, paddingHorizontal: 16, flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: stitch.surfaceLow },
  langText: { color: stitch.text, fontSize: 16, fontWeight: "800" },
  content: { paddingHorizontal: 32, paddingTop: 42, gap: 16 },
  securityImage: { height: 240, borderRadius: 12, overflow: "hidden" },
  title: { marginTop: 16, color: stitch.navy, fontSize: 32, lineHeight: 41, fontWeight: "900", textAlign: "center", letterSpacing: -0.5 },
  subtitle: { color: stitch.muted, fontSize: 16, lineHeight: 25, textAlign: "center", fontWeight: "700" },
  trustGrid: { flexDirection: "row", gap: 14, marginTop: 16, marginBottom: 10 },
  trustCard: { flex: 1, minHeight: 126, alignItems: "center", justifyContent: "center", gap: 12 },
  trustIcon: { width: 56, height: 56, borderRadius: 28, alignItems: "center", justifyContent: "center", backgroundColor: stitch.blueSoft },
  trustTitle: { color: stitch.navy, fontSize: 15, lineHeight: 22, fontWeight: "900", textAlign: "center" },
  googleButton: { height: 52, borderRadius: 8, borderWidth: 1, borderColor: stitch.line, backgroundColor: stitch.surface, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 14 },
  googleIcon: { width: 24, height: 24 },
  googleText: { color: stitch.navy, fontSize: 17, fontWeight: "900" },
  kakaoText: { color: stitch.navy, fontSize: 17, fontWeight: "900" },
  naverText: { color: "#fff", fontSize: 17, fontWeight: "900" },
  notice: { marginTop: 18, padding: 16, flexDirection: "row", gap: 12, backgroundColor: stitch.surfaceLow, borderLeftWidth: 5, borderLeftColor: stitch.line },
  noticeText: { flex: 1, color: stitch.muted, fontSize: 13, lineHeight: 20, fontWeight: "700" },
  terms: { flexDirection: "row", justifyContent: "center", gap: 14, marginTop: 10, marginBottom: 12 },
  termText: { color: stitch.outline, fontSize: 12, fontWeight: "800" },
  dot: { color: stitch.line },
  devBox: { gap: 10, marginTop: 8, marginBottom: 24 },
  input: { minHeight: 48, borderRadius: 8, borderWidth: 1, borderColor: stitch.line, backgroundColor: stitch.surface, paddingHorizontal: 14, color: stitch.text },
  secondaryText: { color: stitch.text, fontWeight: "900", fontSize: 15 },
});
