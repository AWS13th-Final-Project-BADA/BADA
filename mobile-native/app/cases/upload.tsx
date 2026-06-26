import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { MaterialIcons } from "@expo/vector-icons";
import { ApiError, fetchApi } from "@/lib/api";
import { uploadEvidence, type PickedFile } from "@/lib/evidence";
import type { Case, Category, FileType } from "@/lib/types";
import { Card, Chip, RemoteImage, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { stitchImages } from "@/lib/stitchAssets";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

const categories: Array<{ key: Category; label: string; type: FileType }> = [
  { key: "contract", label: t("upload.categories.contract"), type: "pdf" },
  { key: "statement", label: t("upload.categories.statement"), type: "pdf" },
  { key: "payment", label: t("upload.categories.payment"), type: "image" },
  { key: "chat", label: t("upload.categories.chat"), type: "image" },
  { key: "schedule", label: t("upload.categories.schedule"), type: "image" },
  { key: "other", label: t("upload.categories.other"), type: "image" },
];

export default function UploadScreen() {
  const router = useRouter();
  const { locale } = useLocale();
  const { caseId } = useLocalSearchParams<{ caseId?: string }>();
  const routeCaseId = typeof caseId === "string" && caseId.trim() ? caseId : null;
  const [activeCaseId, setActiveCaseId] = useState<string | null>(routeCaseId);
  const [cases, setCases] = useState<Case[]>([]);
  const [loadingCases, setLoadingCases] = useState(!routeCaseId);
  const [category, setCategory] = useState<Category>("contract");
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<Array<{ name: string; status: string }>>([]);

  useEffect(() => {
    let mounted = true;
    if (routeCaseId) {
      setActiveCaseId(routeCaseId);
      setLoadingCases(false);
      return () => {
        mounted = false;
      };
    }

    async function loadCases() {
      try {
        const data = await fetchApi<Case[]>("/cases");
        if (!mounted) return;
        const list = Array.isArray(data) ? data : [];
        setCases(list);
        setActiveCaseId(list[0]?.id ?? null);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
      } finally {
        if (mounted) setLoadingCases(false);
      }
    }

    void loadCases();
    return () => {
      mounted = false;
    };
  }, [routeCaseId, router]);

  const selected = categories.find((item) => item.key === category) || categories[0];
  const selectedCase = useMemo(
    () => cases.find((item) => item.id === activeCaseId) ?? null,
    [activeCaseId, cases],
  );

  async function upload(file: PickedFile) {
    if (!activeCaseId) {
      Alert.alert("사건이 필요해요", "자료를 올리려면 먼저 사건을 만들거나 선택해야 합니다.");
      return;
    }

    setBusy(true);
    try {
      await uploadEvidence(activeCaseId, file, selected.key, selected.type);
      setFiles((prev) => [{ name: file.name, status: "업로드 완료" }, ...prev]);
      Alert.alert("업로드 완료", "증거 자료가 사건 폴더에 추가되었어요.");
    } catch (e: any) {
      Alert.alert("업로드 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function pickCamera() {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("권한이 필요해요", "문서를 촬영하려면 카메라 권한을 허용해 주세요.");
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled) {
      const asset = result.assets[0];
      await upload({
        uri: asset.uri,
        name: asset.fileName || `camera-${Date.now()}.jpg`,
        mimeType: asset.mimeType || "image/jpeg",
      });
    }
  }

  async function pickGallery() {
    const result = await ImagePicker.launchImageLibraryAsync({ quality: 0.8 });
    if (!result.canceled) {
      const asset = result.assets[0];
      await upload({
        uri: asset.uri,
        name: asset.fileName || `image-${Date.now()}.jpg`,
        mimeType: asset.mimeType || "image/jpeg",
      });
    }
  }

  async function pickFile() {
    const result = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true });
    if (!result.canceled) {
      const asset = result.assets[0];
      await upload({
        uri: asset.uri,
        name: asset.name,
        mimeType: asset.mimeType || "application/octet-stream",
      });
    }
  }

  if (loadingCases) {
    return (
      <StitchScreen active="upload">
        <TopBar title={t("upload.title")} back right="help-outline" />
        <View style={styles.loading}>
          <ActivityIndicator color={stitch.blue} />
          <Text style={styles.loadingText}>{t("common.loading")}</Text>
        </View>
      </StitchScreen>
    );
  }

  if (!activeCaseId) {
    return (
      <StitchScreen active="upload">
        <TopBar title={t("upload.title")} back right="help-outline" />
        <View style={styles.empty}>
          <View style={styles.emptyIcon}>
            <MaterialIcons name="folder-open" size={54} color={stitch.blue} />
          </View>
          <Text style={styles.emptyTitle}>{t("upload.emptyTitle")}</Text>
          <Text style={styles.emptyBody}>{t("upload.emptyBody")}</Text>
          <StitchButton onPress={() => router.push("/cases/new")}>{t("cases.create")}</StitchButton>
          <Pressable style={styles.secondaryButton} onPress={() => router.push("/cases")}>
            <Text style={styles.secondaryButtonText}>{t("home.secondary")}</Text>
          </Pressable>
        </View>
      </StitchScreen>
    );
  }

  return (
    <StitchScreen active="upload">
      <TopBar title={t("upload.title")} back right="help-outline" />
      <View style={styles.content}>
        <View style={styles.stepHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>{t("upload.selectCategory")}</Text>
            <Text style={styles.subtitle}>
              {selectedCase?.workplace_name || selectedCase?.employer_name || t("cases.detail")}
            </Text>
          </View>
          <Text style={styles.step}>Step 1 of 2</Text>
        </View>

        {!routeCaseId && cases.length > 1 ? (
          <View style={styles.caseStrip}>
            {cases.slice(0, 4).map((item) => (
              <Pressable key={item.id} onPress={() => setActiveCaseId(item.id)}>
                <Chip
                  label={item.workplace_name || item.employer_name || `사건 ${item.id.slice(0, 4)}`}
                  active={item.id === activeCaseId}
                />
              </Pressable>
            ))}
          </View>
        ) : null}

        <View style={styles.categoryGrid}>
          {categories.map((item) => (
            <Pressable key={item.key} onPress={() => setCategory(item.key)}>
              <Chip label={item.label} active={item.key === category} />
            </Pressable>
          ))}
        </View>

        <RemoteImage uri={stitchImages.uploadDoc} style={styles.uploadPreview} />

        <View style={styles.methodGrid}>
          <UploadMethod icon="photo-camera" title="사진 촬영" body="종이 문서 촬영" onPress={pickCamera} />
          <UploadMethod icon="image" title="갤러리" body="이미지 선택" onPress={pickGallery} />
          <UploadMethod icon="upload-file" title="파일" body="PDF/문서 선택" onPress={pickFile} />
        </View>

        <Card style={styles.privacy}>
          <MaterialIcons name="shield" size={24} color={stitch.blue} />
          <Text style={styles.privacyText}>{t("upload.tip")}</Text>
        </Card>

        <View style={styles.attachTop}>
          <Text style={styles.sectionTitle}>{t("upload.currentFiles")}</Text>
          <Text style={styles.count}>{files.length} items</Text>
        </View>
        <Card style={styles.fileList}>
          {files.length ? (
            files.map((file, index) => (
              <View key={`${file.name}-${index}`} style={[styles.fileRow, index < files.length - 1 && styles.fileDivider]}>
                <MaterialIcons name="description" size={24} color={stitch.blue} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
                  <Text style={styles.fileStatus}>{file.status}</Text>
                </View>
                <MaterialIcons name="check-circle" size={22} color={stitch.green} />
              </View>
            ))
          ) : (
            <View style={styles.noFiles}>
              <MaterialIcons name="cloud-upload" size={34} color={stitch.outline} />
              <Text style={styles.noFilesText}>{t("upload.emptyTitle")}</Text>
            </View>
          )}
        </Card>

        <Pressable style={styles.addMore} onPress={pickFile} disabled={busy}>
          <MaterialIcons name="add-circle-outline" size={22} color={stitch.blue} />
          <Text style={styles.addMoreText}>{t("upload.dropzone")}</Text>
        </Pressable>
      </View>
    </StitchScreen>
  );
}

function UploadMethod({
  icon,
  title,
  body,
  onPress,
}: {
  icon: keyof typeof MaterialIcons.glyphMap;
  title: string;
  body: string;
  onPress: () => void;
}) {
  return (
    <Pressable style={styles.method} onPress={onPress}>
      <MaterialIcons name={icon} size={28} color={stitch.blue} />
      <Text style={styles.methodTitle}>{title}</Text>
      <Text style={styles.methodBody}>{body}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 18 },
  loading: { paddingTop: 120, alignItems: "center", gap: 12 },
  loadingText: { color: stitch.outline, fontSize: 13, fontWeight: "700" },
  empty: { padding: 28, paddingTop: 110, gap: 16, alignItems: "center" },
  emptyIcon: { width: 92, height: 92, borderRadius: 46, alignItems: "center", justifyContent: "center", backgroundColor: stitch.blueSoft },
  emptyTitle: { color: stitch.text, fontSize: 24, fontWeight: "900", textAlign: "center" },
  emptyBody: { color: stitch.muted, fontSize: 14, lineHeight: 22, textAlign: "center", marginBottom: 8 },
  secondaryButton: { height: 48, borderRadius: 8, alignItems: "center", justifyContent: "center", paddingHorizontal: 18 },
  secondaryButtonText: { color: stitch.blue, fontSize: 14, fontWeight: "900" },
  stepHeader: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12 },
  title: { color: stitch.text, fontSize: 24, fontWeight: "900" },
  subtitle: { marginTop: 5, color: stitch.muted, fontSize: 13, lineHeight: 19, fontWeight: "700" },
  step: { color: stitch.outline, fontSize: 12, fontWeight: "800", marginTop: 4 },
  caseStrip: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  categoryGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  uploadPreview: { height: 150, borderRadius: 12 },
  methodGrid: { flexDirection: "row", gap: 10 },
  method: { flex: 1, minHeight: 112, borderRadius: 12, backgroundColor: stitch.surface, borderWidth: 1, borderColor: "rgba(198,198,205,0.45)", alignItems: "center", justifyContent: "center", gap: 5, padding: 10 },
  methodTitle: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  methodBody: { color: stitch.outline, fontSize: 11, textAlign: "center", fontWeight: "700" },
  privacy: { padding: 14, flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: stitch.surfaceLow },
  privacyText: { flex: 1, color: stitch.muted, fontSize: 13, lineHeight: 19, fontWeight: "700" },
  attachTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  sectionTitle: { color: stitch.text, fontSize: 18, fontWeight: "900" },
  count: { color: stitch.outline, fontSize: 12, fontWeight: "800" },
  fileList: { overflow: "hidden" },
  fileRow: { flexDirection: "row", alignItems: "center", gap: 12, padding: 14 },
  fileDivider: { borderBottomWidth: 1, borderBottomColor: "rgba(198,198,205,0.28)" },
  fileName: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  fileStatus: { marginTop: 3, color: stitch.outline, fontSize: 12, fontWeight: "700" },
  noFiles: { minHeight: 92, alignItems: "center", justifyContent: "center", gap: 8 },
  noFilesText: { color: stitch.outline, fontSize: 13, fontWeight: "800" },
  addMore: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, height: 48, borderRadius: 8, borderWidth: 1, borderColor: "rgba(0,81,213,0.16)", backgroundColor: "rgba(0,81,213,0.04)" },
  addMoreText: { color: stitch.blue, fontSize: 14, fontWeight: "900" },
});
