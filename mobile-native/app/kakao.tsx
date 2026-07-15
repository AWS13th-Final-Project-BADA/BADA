import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { ApiError, fetchApi } from "@/lib/api";
import { Card, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";
import { MaterialIcons } from "@expo/vector-icons";

// BADA 카카오톡 채널 채팅 딥링크. 채널 ID가 바뀌면 여기만 수정.
const KAKAO_CHANNEL_URL = "http://pf.kakao.com/_WxnXnX/chat";

interface LinkCodeResp {
  code: string;
  guide?: string;
}

export default function KakaoLink() {
  useLocale(); // 언어 변경 시 리렌더
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const issue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchApi<LinkCodeResp>("/auth/kakao/link-code", { method: "POST" });
      setCode(res.code);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError(t("kakao.authError"));
      } else {
        setError(t("kakao.error"));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void issue();
  }, [issue]);

  async function openChannel() {
    try {
      await Linking.openURL(KAKAO_CHANNEL_URL);
    } catch {
      setError(t("kakao.channelError"));
    }
  }

  return (
    <StitchScreen bottom={false}>
      <TopBar title={t("kakao.title")} back />
      <View style={styles.content}>
        <Text style={styles.subtitle}>{t("kakao.subtitle")}</Text>

        <Card style={styles.codeCard}>
          <Text style={styles.codeLabel}>{t("kakao.codeLabel")}</Text>
          {loading ? (
            <ActivityIndicator color={stitch.blue} style={{ marginVertical: 18 }} />
          ) : error ? (
            <Text style={styles.errorText}>{error}</Text>
          ) : (
            <Text style={styles.code}>{code}</Text>
          )}
          <Pressable style={styles.reissue} onPress={issue} disabled={loading}>
            <MaterialIcons name="refresh" size={16} color={stitch.muted} />
            <Text style={styles.reissueText}>{t("kakao.reissue")}</Text>
          </Pressable>
        </Card>

        <View style={styles.steps}>
          <StepRow num="1" text={t("kakao.step1")} />
          <StepRow num="2" text={t("kakao.step2")} />
          <StepRow num="3" text={t("kakao.step3")} />
        </View>

        <StitchButton tone="kakao" icon="chat-bubble-outline" onPress={openChannel} disabled={loading}>
          <Text style={styles.openText}>{t("kakao.openChannel")}</Text>
        </StitchButton>

        <Card style={styles.notice}>
          <MaterialIcons name="info-outline" size={20} color={stitch.outline} />
          <Text style={styles.noticeText}>{t("kakao.guide")}</Text>
        </Card>
      </View>
    </StitchScreen>
  );
}

function StepRow({ num, text }: { num: string; text: string }) {
  return (
    <View style={styles.stepRow}>
      <View style={styles.stepNum}>
        <Text style={styles.stepNumText}>{num}</Text>
      </View>
      <Text style={styles.stepText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 20 },
  subtitle: { color: stitch.muted, fontSize: 14, lineHeight: 21, fontWeight: "700" },
  codeCard: { padding: 24, alignItems: "center", gap: 8 },
  codeLabel: { color: stitch.outline, fontSize: 13, fontWeight: "900" },
  code: { color: stitch.navy, fontSize: 40, lineHeight: 48, fontWeight: "900", letterSpacing: 6, marginVertical: 8 },
  errorText: { color: stitch.amber, fontSize: 14, lineHeight: 20, fontWeight: "700", textAlign: "center", marginVertical: 12 },
  reissue: { flexDirection: "row", alignItems: "center", gap: 5, paddingVertical: 6, paddingHorizontal: 12 },
  reissueText: { color: stitch.muted, fontSize: 13, fontWeight: "800" },
  steps: { gap: 14 },
  stepRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  stepNum: { width: 26, height: 26, borderRadius: 13, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  stepNumText: { color: stitch.blue, fontSize: 13, fontWeight: "900" },
  stepText: { flex: 1, color: stitch.text, fontSize: 14, lineHeight: 20, fontWeight: "700" },
  openText: { color: stitch.navy, fontSize: 17, fontWeight: "900" },
  notice: { padding: 16, flexDirection: "row", gap: 12, alignItems: "center", backgroundColor: stitch.surfaceLow, borderLeftWidth: 5, borderLeftColor: stitch.line },
  noticeText: { flex: 1, color: stitch.muted, fontSize: 13, lineHeight: 19, fontWeight: "700" },
});
