import type { ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, radius, shadow, spacing } from "@/theme";

export function AppScreen({
  children,
  scroll = true,
  padded = true,
}: {
  children: ReactNode;
  scroll?: boolean;
  padded?: boolean;
}) {
  if (!scroll) {
    return <SafeAreaView style={[styles.screen, padded && styles.padded]}>{children}</SafeAreaView>;
  }
  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[styles.scrollContent, padded && styles.padded]}
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function HeroCard({
  eyebrow,
  title,
  body,
  children,
}: {
  eyebrow?: string;
  title: string;
  body?: string;
  children?: ReactNode;
}) {
  return (
    <View style={styles.hero}>
      {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
      <Text style={styles.heroTitle}>{title}</Text>
      {body ? <Text style={styles.heroBody}>{body}</Text> : null}
      {children ? <View style={styles.heroChildren}>{children}</View> : null}
    </View>
  );
}

export function Surface({
  children,
  style,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  return <View style={[styles.surface, style]}>{children}</View>;
}

export function SectionHeader({
  title,
  action,
}: {
  title: string;
  action?: ReactNode;
}) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {action}
    </View>
  );
}

export function PrimaryButton({
  children,
  tone = "dark",
  style,
  ...props
}: PressableProps & {
  children: ReactNode;
  tone?: "dark" | "blue" | "light" | "danger" | "kakao" | "naver";
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <Pressable
      {...props}
      style={({ pressed }) => [
        styles.button,
        toneStyles[tone],
        pressed && styles.pressed,
        props.disabled && styles.disabled,
        typeof style === "function" ? style({ pressed }) : style,
      ]}
    >
      {typeof children === "string" ? (
        <Text style={[styles.buttonText, tone === "light" && styles.buttonTextDark]}>{children}</Text>
      ) : (
        children
      )}
    </Pressable>
  );
}

export function ActionCard({
  title,
  body,
  meta,
  icon = "B",
  tone = "white",
  compact = false,
  onPress,
}: {
  title: string;
  body?: string;
  meta?: string;
  icon?: string;
  tone?: "white" | "blue" | "green" | "amber";
  compact?: boolean;
  onPress?: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.actionCard,
        compact && styles.actionCardCompact,
        actionTones[tone],
        pressed && styles.pressed,
      ]}
    >
      <View style={[styles.actionIcon, tone !== "white" && tone !== "amber" && styles.actionIconDark]}>
        <Text style={[styles.actionIconText, tone !== "white" && tone !== "amber" && { color: "#fff" }]}>{icon}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={[styles.actionTitle, tone !== "white" && tone !== "amber" && { color: "#fff" }]}>{title}</Text>
        {body ? (
          <Text style={[styles.actionBody, tone !== "white" && tone !== "amber" && { color: "rgba(255,255,255,0.78)" }]}>
            {body}
          </Text>
        ) : null}
        {meta ? <Text style={styles.actionMeta}>{meta}</Text> : null}
      </View>
    </Pressable>
  );
}

export function MetricCard({
  label,
  value,
  tone = "slate",
}: {
  label: string;
  value: string;
  tone?: "slate" | "blue" | "green" | "rose";
}) {
  return (
    <View style={[styles.metric, metricTones[tone]]}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

export function Pill({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "blue" | "green" | "rose" | "amber" }) {
  return (
    <Text style={[styles.pill, pillTones[tone]]}>{children}</Text>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <View style={styles.empty}>
      <Text style={styles.emptyIcon}>＋</Text>
      <Text style={styles.emptyTitle}>{title}</Text>
      {body ? <Text style={styles.emptyBody}>{body}</Text> : null}
      {action ? <View style={{ marginTop: spacing.md }}>{action}</View> : null}
    </View>
  );
}

export function LoadingState() {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.primary} />
    </View>
  );
}

export function ErrorText({ message }: { message: string }) {
  return <Text style={styles.error}>{message}</Text>;
}

export function statusTone(status?: string | null): "slate" | "blue" | "green" | "rose" | "amber" {
  if (status === "completed" || status === "done" || status === "ready") return "green";
  if (status === "processing" || status === "analyzing") return "blue";
  if (status === "failed" || status === "blocked") return "rose";
  if (status === "pending" || status === "preparing") return "amber";
  return "slate";
}

export function formatWon(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return `${Math.round(Number(value)).toLocaleString("ko-KR")}원`;
}

export function formatDate(value?: string | null) {
  return value ? value.slice(0, 10) : "—";
}

const toneStyles = StyleSheet.create({
  dark: { backgroundColor: colors.text },
  blue: { backgroundColor: colors.primary },
  light: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border },
  danger: { backgroundColor: colors.danger },
  kakao: { backgroundColor: "#fee500" },
  naver: { backgroundColor: "#03c75a" },
});

const actionTones = StyleSheet.create({
  white: { backgroundColor: colors.card, borderColor: colors.border },
  blue: { backgroundColor: colors.primary, borderColor: colors.primary },
  green: { backgroundColor: colors.success, borderColor: colors.success },
  amber: { backgroundColor: colors.amberSoft, borderColor: "#fde68a" },
});

const metricTones = StyleSheet.create({
  slate: { backgroundColor: colors.badge },
  blue: { backgroundColor: colors.blueSoft },
  green: { backgroundColor: colors.greenSoft },
  rose: { backgroundColor: colors.roseSoft },
});

const pillTones = StyleSheet.create({
  slate: { backgroundColor: colors.badge, color: colors.textMuted },
  blue: { backgroundColor: colors.blueSoft, color: colors.primary },
  green: { backgroundColor: colors.greenSoft, color: colors.success },
  rose: { backgroundColor: colors.roseSoft, color: colors.danger },
  amber: { backgroundColor: colors.amberSoft, color: colors.warning },
});

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  scrollContent: {
    gap: spacing.md,
    paddingBottom: spacing.xxl,
  },
  padded: {
    padding: spacing.md,
  },
  hero: {
    borderRadius: radius.xl,
    padding: spacing.lg,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: "rgba(203,213,225,0.85)",
    ...shadow.card,
  },
  eyebrow: {
    alignSelf: "flex-start",
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    borderRadius: radius.full,
    backgroundColor: colors.blueSoft,
    color: colors.primary,
    fontSize: 12,
    fontWeight: "800",
    overflow: "hidden",
  },
  heroTitle: {
    marginTop: spacing.md,
    fontSize: 30,
    lineHeight: 36,
    fontWeight: "900",
    color: colors.text,
  },
  heroBody: {
    marginTop: spacing.sm,
    color: colors.textMuted,
    fontSize: 15,
    lineHeight: 24,
    fontWeight: "600",
  },
  heroChildren: {
    marginTop: spacing.lg,
  },
  surface: {
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card,
    padding: spacing.md,
    ...shadow.card,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "900",
    color: colors.text,
  },
  button: {
    minHeight: 52,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    alignItems: "center",
    justifyContent: "center",
    ...shadow.soft,
  },
  buttonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "800",
  },
  buttonTextDark: {
    color: colors.text,
  },
  pressed: {
    opacity: 0.86,
    transform: [{ scale: 0.99 }],
  },
  disabled: {
    opacity: 0.45,
  },
  actionCard: {
    minHeight: 116,
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: spacing.md,
    flexDirection: "row",
    gap: spacing.sm,
    ...shadow.card,
  },
  actionCardCompact: {
    minHeight: 96,
    padding: spacing.sm + 2,
  },
  actionIcon: {
    width: 42,
    height: 42,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.blueSoft,
  },
  actionIconDark: {
    backgroundColor: "rgba(255,255,255,0.18)",
  },
  actionIconText: {
    color: colors.primary,
    fontWeight: "900",
    fontSize: 13,
  },
  actionTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
    lineHeight: 22,
  },
  actionBody: {
    marginTop: 4,
    color: colors.textMuted,
    fontSize: 13,
    fontWeight: "600",
    lineHeight: 20,
  },
  actionMeta: {
    marginTop: spacing.sm,
    color: colors.textSoft,
    fontSize: 12,
    fontWeight: "700",
  },
  metric: {
    flex: 1,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  metricLabel: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: "800",
  },
  metricValue: {
    marginTop: 6,
    color: colors.text,
    fontSize: 19,
    fontWeight: "900",
  },
  pill: {
    alignSelf: "flex-start",
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    fontSize: 12,
    fontWeight: "800",
    overflow: "hidden",
  },
  empty: {
    borderRadius: radius.lg,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: "#cbd5e1",
    backgroundColor: "rgba(255,255,255,0.72)",
    padding: spacing.xl,
    alignItems: "center",
  },
  emptyIcon: {
    fontSize: 30,
    color: colors.textSoft,
  },
  emptyTitle: {
    marginTop: spacing.sm,
    fontSize: 16,
    color: colors.text,
    fontWeight: "900",
    textAlign: "center",
  },
  emptyBody: {
    marginTop: spacing.xs,
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
    textAlign: "center",
  },
  center: {
    flex: 1,
    minHeight: 220,
    justifyContent: "center",
    alignItems: "center",
  },
  error: {
    borderRadius: radius.md,
    backgroundColor: colors.roseSoft,
    color: colors.danger,
    padding: spacing.md,
    fontSize: 13,
    fontWeight: "700",
    lineHeight: 20,
    overflow: "hidden",
  },
});
