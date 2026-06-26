import { useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { fetchApi } from "@/lib/api";
import type { CommunityCategory, CommunityPost } from "@/lib/types";
import { COMMUNITY_CATEGORY_LABELS } from "@/lib/types";
import { Card, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

const CATEGORIES: CommunityCategory[] = ["free", "wage", "petition", "review", "translation"];

export default function NewPost() {
  const router = useRouter();
  const { locale } = useLocale();
  const [category, setCategory] = useState<CommunityCategory>("free");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (title.trim().length < 2 || content.trim().length < 2) {
      Alert.alert("입력 확인", "제목과 내용을 2자 이상 입력해 주세요.");
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
    <StitchScreen active="community">
      <TopBar title={t("community.write")} back />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View>
          <Text style={styles.title}>{t("community.write")}</Text>
          <Text style={styles.subtitle}>{t("community.subtitle")}</Text>
        </View>

        <Card style={styles.formCard}>
          <View style={styles.field}>
            <Text style={styles.label}>카테고리</Text>
            <View style={styles.chips}>
              {CATEGORIES.map((item) => {
                const active = item === category;
                return (
                  <Pressable
                    key={item}
                    style={[styles.chip, active && styles.chipOn]}
                    onPress={() => setCategory(item)}
                  >
                    <Text style={[styles.chipText, active && styles.chipTextOn]}>
                      {t("community.categories." + item)}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>{t("community.titlePlaceholder")}</Text>
            <TextInput
              style={styles.input}
              value={title}
              onChangeText={setTitle}
              placeholder={t("community.titlePlaceholder")}
              placeholderTextColor={stitch.outline}
              maxLength={160}
            />
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>{t("community.contentPlaceholder")}</Text>
            <TextInput
              style={[styles.input, styles.textarea]}
              value={content}
              onChangeText={setContent}
              placeholder={t("community.contentPlaceholder")}
              placeholderTextColor={stitch.outline}
              multiline
              maxLength={5000}
            />
          </View>
        </Card>

        <Card style={styles.safety}>
          <MaterialIcons name="verified-user" size={22} color={stitch.blue} />
          <Text style={styles.safetyText}>{t("disclaimer")}</Text>
        </Card>

        <StitchButton icon="edit" onPress={submit} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : t("community.submit")}
        </StitchButton>
      </ScrollView>
    </StitchScreen>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 18, paddingBottom: 112 },
  title: { color: stitch.text, fontSize: 26, lineHeight: 34, fontWeight: "900" },
  subtitle: { marginTop: 6, color: stitch.muted, fontSize: 14, lineHeight: 21, fontWeight: "700" },
  formCard: { padding: 18, gap: 18 },
  field: { gap: 8 },
  label: { color: stitch.muted, fontSize: 12, fontWeight: "900" },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { borderRadius: 999, backgroundColor: stitch.surfaceHigh, paddingHorizontal: 14, paddingVertical: 8 },
  chipOn: { backgroundColor: stitch.navy },
  chipText: { color: stitch.muted, fontSize: 12, fontWeight: "900" },
  chipTextOn: { color: "#fff" },
  input: { minHeight: 48, borderWidth: 1, borderColor: "rgba(198,198,205,0.65)", borderRadius: 8, paddingHorizontal: 12, backgroundColor: stitch.surface, color: stitch.text, fontSize: 15, fontWeight: "700" },
  textarea: { minHeight: 180, paddingTop: 12, textAlignVertical: "top", lineHeight: 22 },
  safety: { padding: 14, flexDirection: "row", gap: 10, backgroundColor: stitch.surfaceLow },
  safetyText: { flex: 1, color: stitch.muted, fontSize: 12, lineHeight: 18, fontWeight: "700" },
});
