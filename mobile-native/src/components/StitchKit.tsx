import type { ReactNode } from "react";
import { Image, Pressable, ScrollView, StyleSheet, Text, View, type StyleProp, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";

export const stitch = {
  bg: "#f7f9fb",
  surface: "#ffffff",
  surfaceLow: "#f2f4f6",
  surfaceHigh: "#e6e8ea",
  text: "#191c1e",
  muted: "#45464d",
  outline: "#76777d",
  line: "#c6c6cd",
  navy: "#000000",
  blue: "#0051d5",
  blueStrong: "#316bf3",
  blueSoft: "#dbe1ff",
  green: "#009668",
  greenSoft: "#e6fbf3",
  red: "#ba1a1a",
  redSoft: "#ffdad6",
  amber: "#b45309",
  amberSoft: "#fff7df",
};

export function StitchScreen({
  children,
  scroll = true,
  bottom = true,
  active,
}: {
  children: ReactNode;
  scroll?: boolean;
  bottom?: boolean;
  active?: "home" | "cases" | "upload" | "assistant" | "community";
}) {
  const body = scroll ? (
    <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={[s.scroll, bottom && s.withBottomNav]}>
      {children}
    </ScrollView>
  ) : (
    <View style={[s.fill, bottom && s.withBottomNav]}>{children}</View>
  );

  return (
    <SafeAreaView style={s.screen}>
      {body}
      {bottom ? <BottomNav active={active} /> : null}
    </SafeAreaView>
  );
}

export function TopBar({
  title = "BADA",
  back = false,
  right = "notifications-none",
}: {
  title?: string;
  back?: boolean;
  right?: keyof typeof MaterialIcons.glyphMap;
}) {
  const router = useRouter();
  return (
    <View style={s.topbar}>
      <Pressable style={s.topIcon} onPress={() => (back ? router.back() : undefined)}>
        <MaterialIcons name={back ? "arrow-back" : "account-circle"} size={24} color={stitch.navy} />
      </Pressable>
      <Text style={s.topTitle} numberOfLines={1}>{title}</Text>
      <Pressable style={s.topIcon}>
        <MaterialIcons name={right} size={24} color={right === "more-horiz" ? stitch.outline : stitch.navy} />
      </Pressable>
    </View>
  );
}

export function BottomNav({ active }: { active?: "home" | "cases" | "upload" | "assistant" | "community" }) {
  const router = useRouter();
  return (
    <View style={s.bottomNav}>
      <Tab icon="home" label="홈" active={active === "home"} onPress={() => router.push("/")} />
      <Tab icon="folder-open" label="사건" active={active === "cases"} onPress={() => router.push("/cases")} />
      <Pressable style={s.centerTab} onPress={() => router.push("/cases/upload")}>
        <MaterialIcons name="add" size={32} color="#fff" />
      </Pressable>
      <Tab icon="smart-toy" label="AI" active={active === "assistant"} onPress={() => router.push("/chat")} />
      <Tab icon="forum" label="커뮤니티" active={active === "community"} onPress={() => router.push("/community")} />
    </View>
  );
}

function Tab({ icon, label, active, onPress }: { icon: keyof typeof MaterialIcons.glyphMap; label: string; active?: boolean; onPress: () => void }) {
  return (
    <Pressable style={s.tab} onPress={onPress}>
      <MaterialIcons name={icon} size={24} color={active ? stitch.blue : stitch.outline} />
      <Text style={[s.tabText, active && s.tabTextOn]}>{label}</Text>
    </Pressable>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[s.card, style]}>{children}</View>;
}

export function StitchButton({
  children,
  onPress,
  tone = "primary",
  icon,
  disabled,
}: {
  children: ReactNode;
  onPress?: () => void;
  tone?: "primary" | "secondary" | "google" | "kakao" | "naver" | "blue";
  icon?: keyof typeof MaterialIcons.glyphMap;
  disabled?: boolean;
}) {
  return (
    <Pressable onPress={onPress} disabled={disabled} style={({ pressed }) => [s.button, buttonTone[tone], pressed && s.pressed, disabled && s.disabled]}>
      {icon ? <MaterialIcons name={icon} size={22} color={tone === "primary" || tone === "blue" || tone === "naver" ? "#fff" : stitch.text} /> : null}
      {typeof children === "string" ? <Text style={[s.buttonText, (tone === "secondary" || tone === "google" || tone === "kakao") && s.buttonTextDark]}>{children}</Text> : children}
    </Pressable>
  );
}

export function Chip({ label, active = false, tone = "default" }: { label: string; active?: boolean; tone?: "default" | "green" | "red" | "blue" }) {
  return (
    <View style={[s.chip, active && s.chipOn, tone === "green" && s.chipGreen, tone === "red" && s.chipRed, tone === "blue" && s.chipBlue]}>
      <Text style={[s.chipText, active && s.chipTextOn, tone === "green" && s.chipTextGreen, tone === "red" && s.chipTextRed, tone === "blue" && s.chipTextBlue]}>{label}</Text>
    </View>
  );
}

export function SectionLabel({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <View style={s.sectionRow}>
      <Text style={s.sectionLabel}>{children}</Text>
      {action}
    </View>
  );
}

export function RemoteImage({ uri, style }: { uri: string; style?: StyleProp<ViewStyle> }) {
  return <Image source={{ uri }} style={[s.remoteImage, style as any]} resizeMode="cover" />;
}

export const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: stitch.bg },
  fill: { flex: 1 },
  scroll: { paddingBottom: 24 },
  withBottomNav: { paddingBottom: 104 },
  topbar: {
    height: 56,
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "rgba(247,249,251,0.96)",
    borderBottomWidth: 1,
    borderBottomColor: "rgba(198,198,205,0.32)",
  },
  topIcon: { width: 40, height: 40, alignItems: "center", justifyContent: "center", borderRadius: 20 },
  topTitle: { color: stitch.navy, fontSize: 24, lineHeight: 32, fontWeight: "800", letterSpacing: -0.2, flex: 1, textAlign: "center" },
  bottomNav: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: 76,
    paddingBottom: 8,
    paddingHorizontal: 8,
    backgroundColor: "rgba(255,255,255,0.96)",
    borderTopWidth: 1,
    borderTopColor: "rgba(198,198,205,0.45)",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
  },
  tab: { flex: 1, height: 58, alignItems: "center", justifyContent: "center", gap: 2 },
  tabText: { color: stitch.outline, fontSize: 11, lineHeight: 14, fontWeight: "600" },
  tabTextOn: { color: stitch.blue },
  centerTab: {
    width: 64,
    height: 64,
    borderRadius: 32,
    marginTop: -28,
    backgroundColor: stitch.navy,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#0f172a",
    shadowOpacity: 0.22,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  card: {
    backgroundColor: stitch.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(198,198,205,0.5)",
    shadowColor: "#0f172a",
    shadowOpacity: 0.045,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  button: {
    height: 52,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 10,
  },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "800" },
  buttonTextDark: { color: stitch.text },
  pressed: { opacity: 0.82, transform: [{ scale: 0.99 }] },
  disabled: { opacity: 0.5 },
  chip: { borderRadius: 999, backgroundColor: stitch.surfaceHigh, paddingHorizontal: 14, paddingVertical: 8 },
  chipOn: { backgroundColor: stitch.navy },
  chipGreen: { backgroundColor: "rgba(0,150,104,0.1)" },
  chipRed: { backgroundColor: stitch.redSoft },
  chipBlue: { backgroundColor: stitch.blueSoft },
  chipText: { color: stitch.muted, fontSize: 12, fontWeight: "700" },
  chipTextOn: { color: "#fff" },
  chipTextGreen: { color: stitch.green },
  chipTextRed: { color: stitch.red },
  chipTextBlue: { color: stitch.blue },
  sectionRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20 },
  sectionLabel: { color: stitch.outline, fontSize: 12, lineHeight: 16, fontWeight: "800", textTransform: "uppercase" },
  remoteImage: { width: "100%", backgroundColor: stitch.surfaceLow },
});

const buttonTone = StyleSheet.create({
  primary: { backgroundColor: stitch.navy },
  blue: { backgroundColor: stitch.blueStrong },
  secondary: { backgroundColor: stitch.surface, borderWidth: 1, borderColor: stitch.line },
  google: { backgroundColor: stitch.surface, borderWidth: 1, borderColor: stitch.line },
  kakao: { backgroundColor: "#fee500" },
  naver: { backgroundColor: "#03c75a" },
});
