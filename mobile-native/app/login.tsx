import { useState } from "react";
import { Alert, Image, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { login } from "@/lib/auth";
import { stitchImages } from "@/lib/stitchAssets";
import { Card, RemoteImage, StitchButton, StitchScreen, stitch } from "@/components/StitchKit";
import { SUPPORTED, setLocale, t, i18n } from "@/i18n";
import type { Locale } from "@/i18n";

export default function Login() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [locale, setLocaleState] = useState<Locale>(i18n.locale as Locale);
  const [langOpen, setLangOpen] = useState(false);

  function changeLanguage(lang: Locale) {
    setLocale(lang);
    setLocaleState(lang);
    setLangOpen(false);
  }

  async function doLogin(provider: "google" | "kakao" | "naver") {
    setBusy(true);
    try {
      const ok = await login(provider);
      if (ok) router.replace("/");
      else Alert.alert("로그인 실패", "토큰을 받지 못했어요. 계정을 다시 선택해 주세요.");
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
        <Pressable style={styles.lang} onPress={() => setLangOpen(true)}>
          <MaterialIcons name="translate" size={20} color={stitch.text} />
          <Text style={styles.langText}>{t("common.locales." + locale)}</Text>
          <MaterialIcons name="expand-more" size={22} color={stitch.text} />
        </Pressable>
      </View>

      <Modal visible={langOpen} transparent animationType="fade" onRequestClose={() => setLangOpen(false)}>
        <Pressable style={styles.modalOverlay} onPress={() => setLangOpen(false)}>
          <View style={styles.langMenu}>
            {SUPPORTED.map((lang) => (
              <Pressable key={lang} style={[styles.langOption, lang === locale && styles.langOptionActive]} onPress={() => changeLanguage(lang)}>
                <Text style={[styles.langOptionText, lang === locale && styles.langOptionTextActive]}>
                  {t("common.locales." + lang)}
                </Text>
                {lang === locale && <MaterialIcons name="check" size={18} color={stitch.blue} />}
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>

      <View style={styles.content}>
        <RemoteImage uri={stitchImages.loginSecurity} style={styles.securityImage} />

        <Text style={styles.title}>{t("login.title")}</Text>
        <Text style={styles.subtitle}>{t("login.subtitle")}</Text>

        <View style={styles.trustGrid}>
          <TrustCard icon="shield" title={t("login.trustData")} />
          <TrustCard icon="gavel" title={t("login.trustNoJudge")} />
        </View>


        <Pressable style={styles.googleButton} onPress={() => doLogin("google")} disabled={busy}>
          <Image source={{ uri: stitchImages.google }} style={styles.googleIcon} />
          <Text style={styles.googleText}>{t("login.google")}</Text>
        </Pressable>
        <StitchButton tone="kakao" icon="chat-bubble-outline" onPress={() => doLogin("kakao")} disabled={busy}>
          <Text style={styles.kakaoText}>{t("login.kakao")}</Text>
        </StitchButton>
        <StitchButton tone="naver" onPress={() => doLogin("naver")} disabled={busy}>
          <Text style={styles.naverText}>{t("login.naver")}</Text>
        </StitchButton>

        <Card style={styles.notice}>
          <MaterialIcons name="info-outline" size={22} color={stitch.outline} />
          <Text style={styles.noticeText}>{t("login.safe")}</Text>
        </Card>

        <View style={styles.terms}>
          <Text style={styles.termText}>이용약관</Text>
          <Text style={styles.dot}>·</Text>
          <Text style={styles.termText}>개인정보처리방침</Text>
        </View>

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
  logo: { color: stitch.navy, fontSize: 34, lineHeight: 42, fontWeight: "900" },
  lang: { height: 46, borderRadius: 23, paddingHorizontal: 16, flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: stitch.surfaceLow },
  langText: { color: stitch.text, fontSize: 16, fontWeight: "800" },
  content: { paddingHorizontal: 32, paddingTop: 42, gap: 16 },
  securityImage: { height: 240, borderRadius: 12, overflow: "hidden" },
  title: { marginTop: 16, color: stitch.navy, fontSize: 32, lineHeight: 41, fontWeight: "900", textAlign: "center" },
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
  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.3)", justifyContent: "flex-start", alignItems: "flex-end", paddingTop: 100, paddingRight: 32 },
  langMenu: { backgroundColor: stitch.surface, borderRadius: 12, paddingVertical: 8, minWidth: 160, shadowColor: "#000", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 12, elevation: 8 },
  langOption: { paddingHorizontal: 16, paddingVertical: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  langOptionActive: { backgroundColor: "rgba(0,81,213,0.08)" },
  langOptionText: { fontSize: 15, fontWeight: "700", color: stitch.text },
  langOptionTextActive: { color: stitch.blue, fontWeight: "900" },
});
