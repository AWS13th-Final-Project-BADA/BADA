import { useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Modal, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { MaterialIcons } from "@expo/vector-icons";
import { ApiError } from "@/lib/api";
import { t } from "@/i18n";
import { stitch } from "@/components/StitchKit";
import type { CommunitySafetyResult } from "./types";

export function CommunityAction({
  icon,
  label,
  active = false,
  danger = false,
  onPress,
  disabled = false,
}: {
  icon: keyof typeof MaterialIcons.glyphMap;
  label: string;
  active?: boolean;
  danger?: boolean;
  onPress?: () => void;
  disabled?: boolean;
}) {
  const color = danger ? stitch.red : active ? stitch.blue : stitch.outline;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled || !onPress}
      onPress={(event) => { event.stopPropagation(); onPress?.(); }}
      style={({ pressed }) => [styles.action, pressed && styles.pressed, disabled && styles.disabled]}
    >
      <MaterialIcons name={icon} size={21} color={color} />
      <Text style={[styles.actionText, { color }]} numberOfLines={1}>{label}</Text>
    </Pressable>
  );
}

export interface CommunityMenuOption {
  key: string;
  label: string;
  icon: keyof typeof MaterialIcons.glyphMap;
  danger?: boolean;
  onPress: () => void;
}

export function CommunityMenuSheet({
  visible,
  title,
  options,
  onClose,
}: {
  visible: boolean;
  title: string;
  options: CommunityMenuOption[];
  onClose: () => void;
}) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => undefined}>
          <View style={styles.handle} />
          <Text style={styles.sheetTitle}>{title}</Text>
          {options.map((option) => (
            <Pressable
              key={option.key}
              style={({ pressed }) => [styles.menuRow, pressed && styles.menuPressed]}
              onPress={() => {
                onClose();
                option.onPress();
              }}
            >
              <View style={[styles.menuIcon, option.danger && styles.menuIconDanger]}>
                <MaterialIcons name={option.icon} size={20} color={option.danger ? stitch.red : stitch.navy} />
              </View>
              <Text style={[styles.menuLabel, option.danger && styles.menuLabelDanger]}>{option.label}</Text>
              <MaterialIcons name="chevron-right" size={21} color={stitch.outline} />
            </Pressable>
          ))}
          <Pressable style={styles.cancelButton} onPress={onClose}>
            <Text style={styles.cancelText}>{t("common.cancel")}</Text>
          </Pressable>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const REPORT_REASONS = ["privacy", "spam", "harassment", "misinformation", "other"] as const;

export function CommunityReportSheet({
  visible,
  busy,
  onClose,
  onSubmit,
}: {
  visible: boolean;
  busy: boolean;
  onClose: () => void;
  onSubmit: (reason: string, description: string) => void;
}) {
  const [reason, setReason] = useState<(typeof REPORT_REASONS)[number]>("privacy");
  const [description, setDescription] = useState("");

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView style={styles.overlay} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <Text style={styles.sheetTitle}>{t("community.reportTitle")}</Text>
          <Text style={styles.sheetBody}>{t("community.reportHelp")}</Text>
          <View style={styles.reasonGrid}>
            {REPORT_REASONS.map((item) => {
              const selected = reason === item;
              return (
                <Pressable key={item} onPress={() => setReason(item)} style={[styles.reasonChip, selected && styles.reasonChipOn]}>
                  <Text style={[styles.reasonText, selected && styles.reasonTextOn]}>{t(`community.reportReasons.${item}`)}</Text>
                </Pressable>
              );
            })}
          </View>
          <TextInput
            value={description}
            onChangeText={setDescription}
            placeholder={t("community.reportDescription")}
            placeholderTextColor={stitch.outline}
            multiline
            maxLength={1000}
            style={styles.reportInput}
          />
          <Pressable
            disabled={busy}
            style={({ pressed }) => [styles.reportButton, pressed && styles.pressed, busy && styles.disabled]}
            onPress={() => onSubmit(t(`community.reportReasons.${reason}`), description.trim())}
          >
            {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.reportButtonText}>{t("community.reportSubmit")}</Text>}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

export function CommunitySafetyBanner({ result, checking }: { result: CommunitySafetyResult | null; checking: boolean }) {
  if (checking) {
    return (
      <View style={[styles.safety, styles.safetyChecking]}>
        <ActivityIndicator size="small" color={stitch.blue} />
        <Text style={styles.safetyText}>{t("community.safetyChecking")}</Text>
      </View>
    );
  }

  if (!result) {
    return (
      <View style={styles.safety}>
        <MaterialIcons name="shield" size={20} color={stitch.blue} />
        <Text style={styles.safetyText}>{t("community.safetyHelp")}</Text>
      </View>
    );
  }

  const blocked = !result.allowed;
  const review = result.moderation_status === "review";
  return (
    <View style={[styles.safety, blocked ? styles.safetyBlocked : review ? styles.safetyReview : styles.safetyPassed]}>
      <MaterialIcons name={blocked ? "error-outline" : review ? "info-outline" : "verified-user"} size={20} color={blocked ? stitch.red : review ? stitch.amber : stitch.green} />
      <View style={{ flex: 1 }}>
        <Text style={[styles.safetyTitle, { color: blocked ? stitch.red : review ? stitch.amber : stitch.green }]}>
          {blocked ? t("community.safetyBlocked") : review ? t("community.safetyReview") : t("community.safetyPassed")}
        </Text>
        <Text style={styles.safetyText}>{result.message}</Text>
        {result.suggested_text ? <Text style={styles.suggestion}>{result.suggested_text}</Text> : null}
      </View>
    </View>
  );
}

export function communityErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) return error instanceof Error ? error.message : fallback;
  const marker = error.message.indexOf(": ");
  const raw = marker >= 0 ? error.message.slice(marker + 2) : "";
  try {
    const parsed = JSON.parse(raw);
    const detail = parsed?.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail.message === "string") return detail.message;
  } catch {
    // Keep the localized fallback for non-JSON errors.
  }
  return fallback;
}

export function formatCommunityDate(value: string, locale: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  try {
    return new Intl.DateTimeFormat(locale, { month: "short", day: "numeric" }).format(date);
  } catch {
    return value.slice(0, 10);
  }
}


const styles = StyleSheet.create({
  action: { minHeight: 38, paddingHorizontal: 5, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 5 },
  actionText: { fontSize: 12, fontWeight: "800" },
  pressed: { opacity: 0.65 },
  disabled: { opacity: 0.5 },
  overlay: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(15,23,42,0.32)" },
  sheet: { backgroundColor: stitch.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, paddingHorizontal: 20, paddingTop: 10, paddingBottom: 28, shadowColor: "#000", shadowOpacity: 0.16, shadowRadius: 18, elevation: 16 },
  handle: { width: 40, height: 4, borderRadius: 2, backgroundColor: stitch.line, alignSelf: "center", marginBottom: 18 },
  sheetTitle: { color: stitch.text, fontSize: 19, lineHeight: 26, fontWeight: "900" },
  sheetBody: { marginTop: 5, color: stitch.muted, fontSize: 13, lineHeight: 19, fontWeight: "600" },
  menuRow: { minHeight: 58, flexDirection: "row", alignItems: "center", gap: 12, borderBottomWidth: 1, borderBottomColor: "rgba(198,198,205,0.3)" },
  menuPressed: { backgroundColor: stitch.surfaceLow },
  menuIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: stitch.surfaceLow, alignItems: "center", justifyContent: "center" },
  menuIconDanger: { backgroundColor: stitch.redSoft },
  menuLabel: { flex: 1, color: stitch.text, fontSize: 15, fontWeight: "800" },
  menuLabelDanger: { color: stitch.red },
  cancelButton: { height: 48, borderRadius: 10, backgroundColor: stitch.surfaceLow, alignItems: "center", justifyContent: "center", marginTop: 14 },
  cancelText: { color: stitch.muted, fontSize: 15, fontWeight: "800" },
  reasonGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 18 },
  reasonChip: { paddingHorizontal: 13, paddingVertical: 9, borderRadius: 999, backgroundColor: stitch.surfaceLow, borderWidth: 1, borderColor: "transparent" },
  reasonChipOn: { backgroundColor: stitch.blueSoft, borderColor: "rgba(0,81,213,0.25)" },
  reasonText: { color: stitch.muted, fontSize: 12, fontWeight: "800" },
  reasonTextOn: { color: stitch.blue },
  reportInput: { minHeight: 88, marginTop: 14, padding: 12, borderRadius: 10, borderWidth: 1, borderColor: stitch.line, backgroundColor: stitch.surface, color: stitch.text, fontSize: 14, lineHeight: 20, textAlignVertical: "top" },
  reportButton: { height: 50, marginTop: 14, borderRadius: 10, backgroundColor: stitch.navy, alignItems: "center", justifyContent: "center" },
  reportButtonText: { color: "#fff", fontSize: 15, fontWeight: "900" },
  safety: { padding: 14, borderRadius: 10, flexDirection: "row", alignItems: "flex-start", gap: 10, backgroundColor: stitch.blueSoft, borderWidth: 1, borderColor: "rgba(0,81,213,0.12)" },
  safetyChecking: { alignItems: "center" },
  safetyPassed: { backgroundColor: stitch.greenSoft, borderColor: "rgba(0,150,104,0.18)" },
  safetyReview: { backgroundColor: stitch.amberSoft, borderColor: "rgba(180,83,9,0.18)" },
  safetyBlocked: { backgroundColor: stitch.redSoft, borderColor: "rgba(186,26,26,0.18)" },
  safetyTitle: { marginBottom: 3, fontSize: 13, fontWeight: "900" },
  safetyText: { flex: 1, color: stitch.muted, fontSize: 12, lineHeight: 18, fontWeight: "600" },
  suggestion: { marginTop: 7, color: stitch.text, fontSize: 12, lineHeight: 18, fontWeight: "700" },
});