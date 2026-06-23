import { useEffect, useState } from "react";
import { View, Text, StyleSheet, Pressable, ScrollView } from "react-native";
import { useRouter } from "expo-router";
import { isLoggedIn } from "@/lib/api";
import { logout } from "@/lib/auth";
import { t } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

export default function Home() {
  const router = useRouter();
  const [authed, setAuthed] = useState(false);

  async function refresh() {
    setAuthed(await isLoggedIn());
  }
  useEffect(() => {
    refresh();
  }, []);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.brand}>BADA</Text>
      <Text style={styles.tagline}>{t("common.tagline")}</Text>

      <View style={styles.menu}>
        <MenuButton
          label={t("nav.cases")}
          onPress={() => router.push("/cases")}
        />
        <MenuButton
          label={t("nav.community") + " · " + t("nav.chat")}
          muted
          onPress={() => {}}
        />
        <MenuButton label="GPS 근무 증거" onPress={() => router.push("/gps")} />
      </View>

      {authed ? (
        <Pressable
          style={styles.secondary}
          onPress={async () => {
            await logout();
            refresh();
          }}
        >
          <Text style={styles.secondaryText}>{t("common.logout")}</Text>
        </Pressable>
      ) : (
        <Pressable style={styles.primary} onPress={() => router.push("/login")}>
          <Text style={styles.primaryText}>{t("common.login")}</Text>
        </Pressable>
      )}

      <Text style={styles.disclaimer}>{t("disclaimer")}</Text>
    </ScrollView>
  );
}

function MenuButton({
  label,
  onPress,
  muted,
}: {
  label: string;
  onPress: () => void;
  muted?: boolean;
}) {
  return (
    <Pressable
      style={[styles.card, muted && { opacity: 0.5 }]}
      onPress={onPress}
    >
      <Text style={styles.cardText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.md },
  brand: { fontSize: 40, fontWeight: "800", color: colors.primary },
  tagline: { fontSize: 15, color: colors.textMuted, marginBottom: spacing.lg },
  menu: { gap: spacing.sm },
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.lg,
  },
  cardText: { fontSize: 16, fontWeight: "600", color: colors.text },
  primary: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
    marginTop: spacing.md,
  },
  primaryText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  secondary: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
    marginTop: spacing.md,
  },
  secondaryText: { color: colors.textMuted, fontWeight: "600" },
  disclaimer: {
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
    marginTop: spacing.xl,
  },
});
