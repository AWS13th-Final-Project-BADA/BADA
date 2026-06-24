import { useState } from "react";
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { useLocalSearchParams } from "expo-router";
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { MaterialIcons } from "@expo/vector-icons";
import { uploadEvidence, type PickedFile } from "@/lib/evidence";
import type { Category, FileType } from "@/lib/types";
import { Card, Chip, RemoteImage, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { stitchImages } from "@/lib/stitchAssets";

const categories: Array<{ key: Category; label: string; type: FileType }> = [
  { key: "contract", label: "계약서", type: "pdf" },
  { key: "statement", label: "급여명세서", type: "pdf" },
  { key: "payment", label: "입금내역", type: "image" },
  { key: "chat", label: "대화 캡처", type: "image" },
  { key: "schedule", label: "근무기록", type: "image" },
  { key: "other", label: "기타", type: "image" },
];

export default function UploadScreen() {
  const { caseId = "demo-case-1" } = useLocalSearchParams<{ caseId?: string }>();
  const [category, setCategory] = useState<Category>("contract");
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<Array<{ name: string; status: string }>>([
    { name: "근로계약서.pdf", status: "1.2 MB · 업로드 중" },
    { name: "입금내역_20260624.jpg", status: "완료 · 2026.06.24" },
  ]);

  const selected = categories.find((item) => item.key === category) || categories[0];

  async function upload(file: PickedFile) {
    setBusy(true);
    try {
      await uploadEvidence(caseId, file, selected.key, selected.type);
      setFiles((prev) => [{ name: file.name, status: "완료 · 방금 전" }, ...prev]);
      Alert.alert("업로드 완료", "증거자료가 사건 폴더에 추가됐어요.");
    } catch (e: any) {
      Alert.alert("업로드 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function pickCamera() {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("권한 필요", "카메라 권한을 허용해 주세요.");
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

  return (
    <StitchScreen active="upload">
      <TopBar title="자료 업로드" back right="help-outline" />
      <View style={styles.content}>
        <View style={styles.stepHeader}>
          <Text style={styles.title}>자료 종류를 선택하세요</Text>
          <Text style={styles.step}>Step 1 of 2</Text>
        </View>

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
          <Text style={styles.privacyText}>업로드한 자료는 상담 준비와 분석을 위해 안전하게 보관됩니다.</Text>
        </Card>

        <View style={styles.attachTop}>
          <Text style={styles.sectionTitle}>첨부한 증거</Text>
          <Text style={styles.count}>{files.length} items</Text>
        </View>
        <Card style={styles.fileList}>
          {files.map((file, index) => (
            <View key={`${file.name}-${index}`} style={[styles.fileRow, index < files.length - 1 && styles.fileDivider]}>
              <MaterialIcons name="description" size={24} color={stitch.blue} />
              <View style={{ flex: 1 }}>
                <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
                <Text style={styles.fileStatus}>{file.status}</Text>
              </View>
              <MaterialIcons name={index === 0 ? "close" : "visibility"} size={22} color={stitch.outline} />
            </View>
          ))}
        </Card>

        <Pressable style={styles.addMore} onPress={pickFile}>
          <MaterialIcons name="add-circle-outline" size={22} color={stitch.blue} />
          <Text style={styles.addMoreText}>파일 더 추가하기</Text>
        </Pressable>

        <StitchButton tone="primary" disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : "검토 후 확인"}
        </StitchButton>
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
  stepHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  title: { color: stitch.text, fontSize: 24, fontWeight: "900" },
  step: { color: stitch.outline, fontSize: 12, fontWeight: "800" },
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
  addMore: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, height: 48, borderRadius: 8, borderWidth: 1, borderColor: "rgba(0,81,213,0.16)", backgroundColor: "rgba(0,81,213,0.04)" },
  addMoreText: { color: stitch.blue, fontSize: 14, fontWeight: "900" },
});
