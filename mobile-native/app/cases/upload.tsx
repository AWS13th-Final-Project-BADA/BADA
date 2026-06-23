import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import { uploadEvidence, type PickedFile } from "@/lib/evidence";
import type { Category } from "@/lib/types";
import { CATEGORY_FILETYPE } from "@/lib/types";
import { t } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

const CATEGORIES: Category[] = [
  "statement",
  "contract",
  "schedule",
  "payment",
  "chat",
  "other",
];

export default function UploadScreen() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const router = useRouter();
  const [category, setCategory] = useState<Category>("statement");
  const [busy, setBusy] = useState(false);

  async function doUpload(file: PickedFile) {
    if (!caseId) return;
    setBusy(true);
    try {
      const fileType = CATEGORY_FILETYPE[category];
      const { via } = await uploadEvidence(caseId, file, category, fileType);
      Alert.alert("업로드 완료", `증거가 등록되었습니다. (${via})`, [
        { text: t("common.confirm"), onPress: () => router.back() },
      ]);
    } catch (e: any) {
      Alert.alert("업로드 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function pickCamera() {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) {
      Alert.alert("권한 필요", "카메라 권한을 허용해 주세요.");
      return;
    }
    const r = await ImagePicker.launchCameraAsync({ quality: 0.7 });
    if (!r.canceled && r.assets[0]) {
      const a = r.assets[0];
      doUpload({
        uri: a.uri,
        name: a.fileName ?? `photo_${Date.now()}.jpg`,
        mimeType: a.mimeType ?? "image/jpeg",
      });
    }
  }

  async function pickGallery() {
    const r = await ImagePicker.launchImageLibraryAsync({ quality: 0.7 });
    if (!r.canceled && r.assets[0]) {
      const a = r.assets[0];
      doUpload({
        uri: a.uri,
        name: a.fileName ?? `image_${Date.now()}.jpg`,
        mimeType: a.mimeType ?? "image/jpeg",
      });
    }
  }

  async function pickDoc() {
    const r = await DocumentPicker.getDocumentAsync({
      type: ["application/pdf", "image/*"],
      copyToCacheDirectory: true,
    });
    if (!r.canceled && r.assets?.[0]) {
      const a = r.assets[0];
      doUpload({
        uri: a.uri,
        name: a.name,
        mimeType: a.mimeType ?? "application/pdf",
      });
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.label}>{t("upload.category")}</Text>
      <View style={styles.chips}>
        {CATEGORIES.map((c) => {
          const on = c === category;
          return (
            <Pressable
              key={c}
              style={[styles.chip, on && styles.chipOn]}
              onPress={() => setCategory(c)}
            >
              <Text style={[styles.chipText, on && styles.chipTextOn]}>
                {t(`upload.categories.${c}`)}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {busy ? (
        <View style={styles.busy}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.muted}>업로드 중...</Text>
        </View>
      ) : (
        <View style={styles.actions}>
          <Pressable style={styles.action} onPress={pickCamera}>
            <Text style={styles.actionText}>📷 사진 촬영</Text>
          </Pressable>
          <Pressable style={styles.action} onPress={pickGallery}>
            <Text style={styles.actionText}>🖼 갤러리에서 선택</Text>
          </Pressable>
          <Pressable style={styles.action} onPress={pickDoc}>
            <Text style={styles.actionText}>📄 파일(PDF) 선택</Text>
          </Pressable>
        </View>
      )}

      <Text style={styles.note}>
        본인이 직접 참여한 대화·본인 자료만 업로드하세요. 민감정보(계좌·주민번호
        등)는 분석 시 자동 가림 처리됩니다.
      </Text>
      <Text style={styles.disclaimer}>{t("disclaimer")}</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.md },
  label: { fontSize: 13, color: colors.textMuted, fontWeight: "600" },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: "#fff",
  },
  chipOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { color: colors.text, fontSize: 13 },
  chipTextOn: { color: "#fff", fontWeight: "600" },
  actions: { gap: spacing.sm, marginTop: spacing.md },
  action: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.lg,
    alignItems: "center",
  },
  actionText: { fontSize: 16, fontWeight: "600", color: colors.text },
  busy: { alignItems: "center", gap: spacing.sm, padding: spacing.xl },
  muted: { color: colors.textMuted },
  note: {
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
    marginTop: spacing.md,
  },
  disclaimer: { fontSize: 12, color: colors.textMuted, lineHeight: 18 },
});
