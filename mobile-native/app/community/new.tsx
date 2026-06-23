import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  Pressable,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { fetchApi } from "@/lib/api";
import type { CommunityCategory, CommunityPost } from "@/lib/types";
import { COMMUNITY_CATEGORY_LABELS } from "@/lib/types";
import { t } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

const CATS: CommunityCategory[] = ["free", "wage", "petition", "review", "translation"];

export default function NewPost() {
  const router = useRouter();
  const [category, setCategory] = useState<CommunityCategory>("free");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (title.trim().length < 2 || content.trim().length < 2) {
      Alert.alert("입력 확인", "제목과 내용을 2자 이상 입력하세요.");
      return;
    }
    setBusy(true);
    try {
      const post = await fetchApi<CommunityPost>("/community/posts", {
        method: "POST",
        body: JSON.stringify({
          category,
          title: title.trim(),
          content: content.trim(),
          language: "auto",
        }),
      });
      router.replace({ pathname: "/community/[id]", params: { id: post.id } });
    } catch (e: any) {
      Alert.alert("등록 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.label}>카테고리</Text>
      <View style={styles.chips}>
        {CATS.map((c) => {
          const on = c === category;
          return (
            <Pressable
              key={c}
              style={[styles.chip, on && styles.chipOn]}
              onPress={() => setCategory(c)}
            >
              <Text style={[styles.chipText, on && styles.chipTextOn]}>
                {COMMUNITY_CATEGORY_LABELS[c]}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={styles.label}>제목</Text>
      <TextInput
        style={styles.input}
        value={title}
        onChangeText={setTitle}
        placeholder="제목을 입력하세요"
        maxLength={160}
      />

      <Text style={styles.label}>내용</Text>
      <TextInput
        style={[styles.input, styles.textarea]}
        value={content}
        onChangeText={setContent}
        placeholder="익명으로 안전하게 공유됩니다. 개인정보(이름·연락처)는 적지 마세요."
        multiline
        maxLength={5000}
      />

      <Pressable style={styles.submit} onPress={submit} disabled={busy}>
        {busy ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.submitText}>{t("common.save")}</Text>
        )}
      </Pressable>

      <Text style={styles.note}>
        게시 전 안전성 검사가 적용됩니다. 위법 단정·타인 비방·개인정보는 가려질 수
        있습니다.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.sm },
  label: { fontSize: 13, color: colors.textMuted, fontWeight: "600", marginTop: spacing.sm },
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
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: spacing.sm,
    backgroundColor: "#fff",
    fontSize: 15,
  },
  textarea: { height: 160, textAlignVertical: "top" },
  submit: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
    marginTop: spacing.md,
  },
  submitText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  note: { fontSize: 12, color: colors.textMuted, lineHeight: 18, marginTop: spacing.sm },
});
