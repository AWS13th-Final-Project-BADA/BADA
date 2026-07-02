import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { MaterialIcons } from "@expo/vector-icons";
import { ApiError, fetchApi } from "@/lib/api";
import { uploadEvidence, type PickedFile } from "@/lib/evidence";
import { scanGallery, uploadApprovedCandidates, type AgentResult, type ScanCandidate } from "@/features/evidence/agent";
import type { Case, Category, FileType } from "@/lib/types";
import { Card, Chip, RemoteImage, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { stitchImages } from "@/lib/stitchAssets";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

const categories: Array<{ key: Category; type: FileType }> = [
  { key: "auto" as Category, type: "image" },
  { key: "contract", type: "pdf" },
  { key: "statement", type: "pdf" },
  { key: "payment", type: "image" },
  { key: "chat", type: "image" },
  { key: "schedule", type: "image" },
  { key: "other", type: "image" },
];

export default function UploadScreen() {
  const router = useRouter();
  const { locale } = useLocale();
  const { caseId } = useLocalSearchParams<{ caseId?: string }>();
  const routeCaseId = typeof caseId === "string" && caseId.trim() ? caseId : null;
  const [activeCaseId, setActiveCaseId] = useState<string | null>(routeCaseId);
  const [cases, setCases] = useState<Case[]>([]);
  const [loadingCases, setLoadingCases] = useState(!routeCaseId);
  const [category, setCategory] = useState<Category>("auto" as Category);
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<Array<{ name: string; status: string; uri?: string }>>([]);
  const [filesExpanded, setFilesExpanded] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<Array<PickedFile & { category: Category }>>([]);
  const [agentResult, setAgentResult] = useState<AgentResult | null>(null);
  const [agentScanning, setAgentScanning] = useState(false);
  const [agentSelected, setAgentSelected] = useState<Set<number>>(new Set());

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
      Alert.alert(t("upload.uploadError"), t("upload.emptyBody"));
      return;
    }
    // 로컬 리스트에 추가 (S3 전송 안 함)
    setPendingFiles((prev) => [...prev, { ...file, category: selected.key }]);
  }

  async function uploadAll() {
    if (!activeCaseId || pendingFiles.length === 0) return;
    setBusy(true);
    let successCount = 0;
    const uploaded: Array<{ name: string; status: string }> = [];
    try {
      for (const pf of pendingFiles) {
        const cat = categories.find((c) => c.key === pf.category) || categories[0];
        await uploadEvidence(activeCaseId, pf, pf.category, cat.type);
        successCount++;
        uploaded.push({ name: pf.name, status: t("upload.done") });
      }
      setFiles((prev) => [...uploaded, ...prev]);
      setPendingFiles([]);
      Alert.alert(t("upload.done"), `${successCount} ${t("upload.done")}`);
    } catch (e: any) {
      // 부분 성공 반영
      if (uploaded.length > 0) {
        setFiles((prev) => [...uploaded, ...prev]);
      }
      Alert.alert(t("upload.uploadError"), String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function pickCamera() {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(t("upload.cameraPermissionTitle"), t("upload.cameraPermissionBody"));
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

  async function pickAudio() {
    const result = await DocumentPicker.getDocumentAsync({
      copyToCacheDirectory: true,
      type: ["audio/*"],
    });
    if (!result.canceled) {
      const asset = result.assets[0];
      await upload({
        uri: asset.uri,
        name: asset.name,
        mimeType: asset.mimeType || "audio/mpeg",
      });
    }
  }

  async function runAgentScan() {
    if (!activeCaseId) return;
    setAgentScanning(true);
    setAgentResult(null);
    setAgentSelected(new Set());
    try {
      const caseData = selectedCase;
      const result = await scanGallery({
        caseId: activeCaseId,
        workStartDate: caseData?.work_start_date || "2026-01-01",
        workEndDate: caseData?.work_end_date || undefined,
        workplaceName: caseData?.workplace_name || undefined,
      });

      // 사용자 확인 없이 바로 업로드 — 서버 classify()가 최종 판별
      if (result.candidates.length > 0) {
        const { uploaded } = await uploadApprovedCandidates(activeCaseId, result.candidates);
        setFiles(prev => [
          ...result.candidates.slice(0, uploaded).map(c => ({ name: c.asset.filename || "image", status: "AI 자동 등록" })),
          ...prev,
        ]);
        Alert.alert(
          "증거 탐색 완료",
          `${result.totalScanned}장 스캔 → ${result.candidates.length}장 후보 → ${uploaded}장 등록 완료.\n서버에서 자동 분류 후 무관 자료는 제외됩니다.`
        );
      } else {
        Alert.alert("증거 탐색 완료", `${result.totalScanned}장을 스캔했지만 관련 파일을 찾지 못했습니다.`);
      }
    } catch (e: any) {
      Alert.alert(t("upload.uploadError"), e?.message || "갤러리 접근 권한을 확인해주세요.");
    } finally {
      setAgentScanning(false);
    }
  }

  function toggleAgentItem(index: number) {
    setAgentSelected(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  async function approveAgentUpload() {
    if (!activeCaseId || !agentResult) return;
    const selected = agentResult.candidates.filter((_, i) => agentSelected.has(i));
    if (!selected.length) { Alert.alert(t("upload.emptyTitle")); return; }

    setBusy(true);
    try {
      const { uploaded } = await uploadApprovedCandidates(activeCaseId, selected);
      setFiles(prev => [
        ...selected.map(c => ({ name: c.asset.filename || "image", status: "에이전트 업로드 완료" })),
        ...prev,
      ]);
      setAgentResult(null);
      Alert.alert(t("upload.done"), `${uploaded} ${t("upload.done")}`);
    } catch (e: any) {
      Alert.alert(t("upload.uploadError"), e?.message || "");
    } finally {
      setBusy(false);
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

      {busy && (
        <View style={styles.uploadOverlay}>
          <View style={styles.uploadModal}>
            <ActivityIndicator size="large" color={stitch.blue} />
            <Text style={styles.uploadModalTitle}>{t("upload.uploading")}</Text>
            <Text style={styles.uploadModalBody}>{t("upload.tip")}</Text>
          </View>
        </View>
      )}

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
              <Chip label={t("upload.categories." + item.key)} active={item.key === category} />
            </Pressable>
          ))}
        </View>

        <RemoteImage uri={stitchImages.uploadDoc} style={styles.uploadPreview} />

        <View style={styles.methodGrid}>
          <UploadMethod icon="photo-camera" title={t("upload.method.camera")} body={t("upload.method.cameraBody")} onPress={pickCamera} />
          <UploadMethod icon="image" title={t("upload.method.gallery")} body={t("upload.method.galleryBody")} onPress={pickGallery} />
          <UploadMethod icon="upload-file" title={t("upload.method.file")} body={t("upload.method.fileBody")} onPress={pickFile} />
          <UploadMethod icon="mic" title={t("upload.method.audio")} body={t("upload.method.audioBody")} onPress={pickAudio} />
        </View>

        {/* 에이전트 스캔 */}
        <Pressable style={styles.agentCard} onPress={runAgentScan} disabled={agentScanning}>
          <View style={styles.agentCardInner}>
            <MaterialIcons name="auto-awesome" size={26} color="#7c3aed" />
            <View style={{ flex: 1 }}>
              <Text style={styles.agentTitle}>AI 증거 탐색</Text>
              <Text style={styles.agentBody}>갤러리에서 증거를 자동으로 찾아드려요</Text>
            </View>
            {agentScanning && <ActivityIndicator size="small" color="#7c3aed" />}
          </View>
        </Pressable>

        <Card style={styles.privacy}>
          <MaterialIcons name="shield" size={24} color={stitch.blue} />
          <Text style={styles.privacyText}>{t("upload.tip")}</Text>
        </Card>

        <View style={styles.attachTop}>
          <Text style={styles.sectionTitle}>{t("upload.currentFiles")}</Text>
          <Text style={styles.count}>{pendingFiles.length + files.length} items</Text>
        </View>
        <Card style={styles.fileList}>
          {pendingFiles.length > 0 && pendingFiles.map((file, index) => (
            <View key={`pending-${file.name}-${index}`} style={[styles.fileRow, styles.fileDivider]}>
              {file.uri && file.mimeType?.startsWith("image") ? (
                <Image source={{ uri: file.uri }} style={styles.fileThumb} />
              ) : (
                <MaterialIcons name="description" size={24} color={stitch.outline} />
              )}
              <View style={{ flex: 1 }}>
                <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
                <Text style={styles.fileStatus}>{t("upload.categories." + file.category)}</Text>
              </View>
              <Pressable onPress={() => setPendingFiles((prev) => prev.filter((_, i) => i !== index))}>
                <MaterialIcons name="close" size={22} color={stitch.outline} />
              </Pressable>
            </View>
          ))}
          {files.length > 0 && (files.length <= 5 || filesExpanded ? files : files.slice(0, 5)).map((file, index) => (
            <View key={`done-${file.name}-${index}`} style={[styles.fileRow, index < Math.min(files.length, filesExpanded ? files.length : 5) - 1 && styles.fileDivider]}>
              {file.uri ? (
                <Image source={{ uri: file.uri }} style={styles.fileThumb} />
              ) : (
                <MaterialIcons name="description" size={24} color={stitch.blue} />
              )}
              <View style={{ flex: 1 }}>
                <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
                <Text style={styles.fileStatus}>{file.status}</Text>
              </View>
              <MaterialIcons name="check-circle" size={22} color={stitch.green} />
            </View>
          ))}
          {files.length > 5 && !filesExpanded && (
            <Pressable style={styles.showMoreRow} onPress={() => setFilesExpanded(true)}>
              <Text style={styles.showMoreText}>{files.length - 5}개 더 보기</Text>
              <MaterialIcons name="expand-more" size={20} color={stitch.blue} />
            </Pressable>
          )}
          {files.length > 5 && filesExpanded && (
            <Pressable style={styles.showMoreRow} onPress={() => setFilesExpanded(false)}>
              <Text style={styles.showMoreText}>접기</Text>
              <MaterialIcons name="expand-less" size={20} color={stitch.blue} />
            </Pressable>
          )}
          {pendingFiles.length === 0 && files.length === 0 && (
            <View style={styles.noFiles}>
              <MaterialIcons name="cloud-upload" size={34} color={stitch.outline} />
              <Text style={styles.noFilesText}>{t("upload.emptyTitle")}</Text>
            </View>
          )}
        </Card>

        {pendingFiles.length > 0 && (
          <StitchButton icon="cloud-upload" onPress={uploadAll}>
            {`${t("upload.uploadExecute")} (${pendingFiles.length})`}
          </StitchButton>
        )}

        {files.length > 0 && pendingFiles.length === 0 && (
          <StitchButton icon="analytics" onPress={() => router.push({ pathname: "/cases/analysis", params: { caseId: activeCaseId } })}>
            {t("upload.readyToAnalyze")}
          </StitchButton>
        )}

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
  fileThumb: { width: 40, height: 40, borderRadius: 6, backgroundColor: "#eee" },
  showMoreRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 4, paddingVertical: 12, borderTopWidth: 1, borderTopColor: "rgba(198,198,205,0.28)" },
  showMoreText: { color: stitch.blue, fontSize: 13, fontWeight: "800" },
  addMore: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, height: 48, borderRadius: 8, borderWidth: 1, borderColor: "rgba(0,81,213,0.16)", backgroundColor: "rgba(0,81,213,0.04)" },
  addMoreText: { color: stitch.blue, fontSize: 14, fontWeight: "900" },
  uploadOverlay: { ...StyleSheet.absoluteFillObject, zIndex: 100, backgroundColor: "rgba(0,0,0,0.5)", alignItems: "center", justifyContent: "center" },
  uploadModal: { backgroundColor: stitch.surface, borderRadius: 16, padding: 32, alignItems: "center", gap: 12, minWidth: 220, shadowColor: "#000", shadowOpacity: 0.2, shadowRadius: 16, elevation: 10 },
  uploadModalTitle: { color: stitch.text, fontSize: 18, fontWeight: "900", marginTop: 8 },
  uploadModalBody: { color: stitch.muted, fontSize: 13, fontWeight: "700", textAlign: "center", lineHeight: 19 },
  agentCard: { borderRadius: 12, borderWidth: 2, borderColor: "#a78bfa", backgroundColor: "#faf5ff", padding: 16 },
  agentCardInner: { flexDirection: "row", alignItems: "center", gap: 12 },
  agentTitle: { color: "#5b21b6", fontSize: 15, fontWeight: "900" },
  agentBody: { color: "#7c3aed", fontSize: 12, fontWeight: "700", marginTop: 2 },
  agentResultCard: { padding: 16, gap: 12 },
  agentResultTitle: { color: stitch.text, fontSize: 16, fontWeight: "900" },
  agentResultSub: { color: stitch.outline, fontSize: 12, fontWeight: "700" },
  candidateRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: "rgba(0,0,0,0.05)" },
  candidateThumb: { width: 40, height: 40, borderRadius: 6, backgroundColor: "#eee" },
  candidateName: { color: stitch.text, fontSize: 13, fontWeight: "800" },
  candidateReason: { color: stitch.outline, fontSize: 11, fontWeight: "600", marginTop: 2 },
  decisionBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4, backgroundColor: "#f3f4f6" },
  decisionRecommend: { backgroundColor: "#dcfce7" },
  decisionText: { fontSize: 11, fontWeight: "800", color: "#374151" },
  agentActions: { flexDirection: "row", gap: 10, marginTop: 4 },
  agentCancel: { flex: 1, height: 44, borderRadius: 8, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: stitch.line },
  agentCancelText: { color: stitch.text, fontSize: 14, fontWeight: "800" },
  agentApprove: { flex: 2, height: 44, borderRadius: 8, backgroundColor: stitch.blue, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
  agentApproveText: { color: "#fff", fontSize: 14, fontWeight: "900" },
});
