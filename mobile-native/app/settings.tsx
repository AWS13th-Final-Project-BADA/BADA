import { Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { fetchApi } from "@/lib/api";
import { logout } from "@/lib/auth";
import { SUPPORTED, t } from "@/i18n";
import type { Locale } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";
import { Card, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { useEffect, useState } from "react";

interface CurrentUser {
  id: string;
  email: string | null;
  name: string | null;
  preferred_lang?: string | null;
  provider?: string | null;
}

export default function SettingsScreen() {
  const router = useRouter();
  const { locale, changeLocale } = useLocale();
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    fetchApi<CurrentUser>("/auth/me").then(setUser).catch(() => {});
  }, []);

  async function signOut() {
    await logout();
    router.replace("/login");
  }

  const displayName = user?.name || user?.email?.split("@")[0] || "";

  return (
    <StitchScreen active="settings">
      <TopBar title={t("nav.settings")} />
      <View style={styles.content}>
        <Card style={styles.profileCard}>
          <View style={styles.avatarCircle}>
            <MaterialIcons name="person" size={32} color={stitch.blue} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.profileName}>{displayName}</Text>
            <Text style={styles.profileEmail}>{user?.email || ""}</Text>
            <Text style={styles.profileProvider}>{user?.provider || ""}</Text>
          </View>
        </Card>

        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>{t("common.language")}</Text>
          <View style={styles.langGrid}>
            {SUPPORTED.map((lang) => (
              <Pressable
                key={lang}
                style={[styles.langChip, lang === locale && styles.langChipActive]}
                onPress={() => changeLocale(lang)}
              >
                <Text style={[styles.langChipText, lang === locale && styles.langChipTextActive]}>
                  {t("common.locales." + lang)}
                </Text>
                {lang === locale && <MaterialIcons name="check" size={16} color={stitch.blue} />}
              </Pressable>
            ))}
          </View>
        </Card>

        <Card style={styles.section}>
          <Pressable style={styles.menuItem} onPress={() => router.push("/gps")}>
            <MaterialIcons name="location-on" size={22} color={stitch.green} />
            <Text style={styles.menuItemText}>{t("gps.title")}</Text>
            <MaterialIcons name="chevron-right" size={22} color={stitch.outline} />
          </Pressable>
          <Pressable style={styles.menuItem} onPress={() => router.push("/kakao")}>
            <MaterialIcons name="chat" size={22} color={stitch.amber} />
            <Text style={styles.menuItemText}>{t("home.kakao")}</Text>
            <MaterialIcons name="chevron-right" size={22} color={stitch.outline} />
          </Pressable>
        </Card>

        <Pressable style={styles.logoutButton} onPress={signOut}>
          <MaterialIcons name="logout" size={20} color={stitch.red} />
          <Text style={styles.logoutText}>{t("common.logout")}</Text>
        </Pressable>
      </View>
    </StitchScreen>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 18 },
  profileCard: { padding: 20, flexDirection: "row", alignItems: "center", gap: 16 },
  avatarCircle: { width: 56, height: 56, borderRadius: 28, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  profileName: { color: stitch.text, fontSize: 18, fontWeight: "900" },
  profileEmail: { color: stitch.muted, fontSize: 13, fontWeight: "700", marginTop: 2 },
  profileProvider: { color: stitch.outline, fontSize: 12, fontWeight: "700", marginTop: 2, textTransform: "capitalize" },
  section: { padding: 16, gap: 12 },
  sectionTitle: { color: stitch.text, fontSize: 16, fontWeight: "900" },
  langGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  langChip: { borderRadius: 999, backgroundColor: stitch.surfaceHigh, paddingHorizontal: 14, paddingVertical: 8, flexDirection: "row", alignItems: "center", gap: 6 },
  langChipActive: { backgroundColor: stitch.blueSoft, borderWidth: 1, borderColor: stitch.blue },
  langChipText: { color: stitch.muted, fontSize: 13, fontWeight: "700" },
  langChipTextActive: { color: stitch.blue, fontWeight: "900" },
  menuItem: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "rgba(198,198,205,0.25)" },
  menuItemText: { flex: 1, color: stitch.text, fontSize: 15, fontWeight: "800" },
  logoutButton: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, height: 48, borderRadius: 8, backgroundColor: stitch.redSoft },
  logoutText: { color: stitch.red, fontSize: 15, fontWeight: "900" },
});
