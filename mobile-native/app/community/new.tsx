import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import type { CommunityCategory, CommunitySafetyResult } from "@/features/community/types";
import {
  checkCommunitySafety,
  createCommunityPost,
  getCommunityPost,
  updateCommunityPost,
} from "@/features/community/api";
import { CommunitySafetyBanner, communityErrorMessage } from "@/features/community/ui";
import { Card, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

const CATEGORIES: CommunityCategory[] = ["free", "wage", "petition", "review", "translation"];

export default function CommunityComposer() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id?: string }>();
  const { locale } = useLocale();
  const postId = typeof params.id === "string" ? params.id : "";
  const editing = Boolean(postId);
  const [category, setCategory] = useState<CommunityCategory>("free");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(editing);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false);
  const [safety, setSafety] = useState<CommunitySafetyResult | null>(null);
  const [checkedSignature, setCheckedSignature] = useState("");
  const [error, setError] = useState("");
  const signature = useMemo(() => `${title.trim()}\n${content.trim()}`, [content, title]);

  useEffect(() => {
    if (!editing) return;
    let alive = true;
    void getCommunityPost(postId)
      .then((post) => {
        if (!alive) return;
        if (!post.my_owned) {
          Alert.alert(t("community.permissionTitle"), t("community.permissionBody"));
          router.back();
          return;
        }
        setCategory(post.category as CommunityCategory);
        setTitle(post.title);
        setContent(post.content);
      })
      .catch((nextError) => setError(communityErrorMessage(nextError, t("community.loadError"))))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [editing, postId, router]);

  function updateTitle(value: string) {
    setTitle(value);
    setSafety(null);
    setCheckedSignature("");
    setError("");
  }

  function updateContent(value: string) {
    setContent(value);
    setSafety(null);
    setCheckedSignature("");
    setError("");
  }

  function validate(): boolean {
    if (title.trim().length < 2) {
      setError(t("community.titleRequired"));
      return false;
    }
    if (content.trim().length < 2) {
      setError(t("community.contentRequired"));
      return false;
    }
    return true;
  }

  async function runSafetyCheck(): Promise<CommunitySafetyResult | null> {
    if (!validate()) return null;
    setChecking(true);
    setError("");
    try {
      const result = await checkCommunitySafety(signature, locale);
      setSafety(result);
      setCheckedSignature(signature);
      return result;
    } catch (nextError) {
      setError(communityErrorMessage(nextError, t("community.safetyFailed")));
      return null;
    } finally {
      setChecking(false);
    }
  }

  async function submit() {
    if (!validate() || busy) return;
    let result = checkedSignature === signature ? safety : null;
    if (!result) result = await runSafetyCheck();
    if (!result || !result.allowed) return;

    setBusy(true);
    setError("");
    try {
      const payload = { category, title: title.trim(), content: content.trim(), language: locale };
      const post = editing
        ? await updateCommunityPost(postId, payload)
        : await createCommunityPost(payload);
      router.replace({ pathname: "/community/[id]", params: { id: post.id } });
    } catch (nextError) {
      setError(communityErrorMessage(nextError, editing ? t("community.updateFailed") : t("community.createFailed")));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <StitchScreen scroll={false} bottom={false}>
        <TopBar title={editing ? t("community.editPost") : t("community.write")} back />
        <View style={styles.center}><ActivityIndicator color={stitch.blue} /></View>
      </StitchScreen>
    );
  }

  return (
    <StitchScreen scroll={false} bottom={false}>
      <KeyboardAvoidingView style={styles.wrap} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <TopBar title={editing ? t("community.editPost") : t("community.write")} back right="check" rightLabel={t("community.submit")} onRightPress={() => void submit()} />
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <View style={styles.heading}>
            <View style={styles.headingIcon}><MaterialIcons name="forum" size={23} color={stitch.blue} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>{editing ? t("community.editTitle") : t("community.composerTitle")}</Text>
              <Text style={styles.subtitle}>{t("community.composerSubtitle")}</Text>
            </View>
          </View>

          <View style={styles.categorySection}>
            <Text style={styles.label}>{t("community.category")}</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
              {CATEGORIES.map((item) => {
                const active = item === category;
                return (
                  <Pressable key={item} style={[styles.chip, active && styles.chipOn]} onPress={() => setCategory(item)}>
                    <Text style={[styles.chipText, active && styles.chipTextOn]}>{t(`community.categories.${item}`)}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>

          <Card style={styles.formCard}>
            <View style={styles.field}>
              <View style={styles.fieldTop}>
                <Text style={styles.label}>{t("community.titlePlaceholder")}</Text>
                <Text style={styles.counter}>{title.length}/160</Text>
              </View>
              <TextInput
                style={styles.input}
                value={title}
                onChangeText={updateTitle}
                placeholder={t("community.titleExample")}
                placeholderTextColor={stitch.outline}
                maxLength={160}
                returnKeyType="next"
              />
            </View>

            <View style={styles.divider} />

            <View style={styles.field}>
              <View style={styles.fieldTop}>
                <Text style={styles.label}>{t("community.contentPlaceholder")}</Text>
                <Text style={styles.counter}>{content.length}/5000</Text>
              </View>
              <TextInput
                style={[styles.input, styles.textarea]}
                value={content}
                onChangeText={updateContent}
                placeholder={t("community.contentExample")}
                placeholderTextColor={stitch.outline}
                multiline
                maxLength={5000}
              />
            </View>
          </Card>

          <View style={styles.safetySection}>
            <View style={styles.safetyHeader}>
              <Text style={styles.sectionTitle}>{t("community.safetyTitle")}</Text>
              <Pressable disabled={checking} style={styles.safetyButton} onPress={() => void runSafetyCheck()}>
                <MaterialIcons name="verified-user" size={17} color={stitch.blue} />
                <Text style={styles.safetyButtonText}>{t("community.safetyCheck")}</Text>
              </Pressable>
            </View>
            <CommunitySafetyBanner result={safety} checking={checking} />
            <Text style={styles.policyNote}>{t("community.safetyPolicy")}</Text>
          </View>

          {error ? (
            <View style={styles.errorBox}>
              <MaterialIcons name="error-outline" size={19} color={stitch.red} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <StitchButton icon={editing ? "save" : "send"} onPress={() => void submit()} disabled={busy || checking}>
            {busy ? <ActivityIndicator color="#fff" /> : editing ? t("community.update") : t("community.submit")}
          </StitchButton>
          <Text style={styles.anonymousNote}>{t("community.anonymousNotice")}</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </StitchScreen>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: stitch.bg },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  content: { padding: 20, gap: 18, paddingBottom: 48 },
  heading: { flexDirection: "row", alignItems: "center", gap: 12 },
  headingIcon: { width: 46, height: 46, borderRadius: 14, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  title: { color: stitch.text, fontSize: 22, lineHeight: 29, fontWeight: "900" },
  subtitle: { marginTop: 3, color: stitch.muted, fontSize: 13, lineHeight: 19, fontWeight: "600" },
  categorySection: { gap: 9 },
  label: { color: stitch.muted, fontSize: 12, fontWeight: "900" },
  chips: { gap: 8, paddingRight: 20 },
  chip: { borderRadius: 999, backgroundColor: stitch.surfaceHigh, paddingHorizontal: 14, paddingVertical: 9 },
  chipOn: { backgroundColor: stitch.navy },
  chipText: { color: stitch.muted, fontSize: 12, fontWeight: "800" },
  chipTextOn: { color: "#fff" },
  formCard: { padding: 17, gap: 17 },
  field: { gap: 9 },
  fieldTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  counter: { color: stitch.outline, fontSize: 10, fontWeight: "700" },
  input: { minHeight: 48, borderRadius: 9, paddingHorizontal: 12, backgroundColor: stitch.surfaceLow, color: stitch.text, fontSize: 15, fontWeight: "600" },
  textarea: { minHeight: 190, paddingTop: 13, textAlignVertical: "top", lineHeight: 22 },
  divider: { height: 1, backgroundColor: "rgba(198,198,205,0.35)" },
  safetySection: { gap: 9 },
  safetyHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  sectionTitle: { color: stitch.text, fontSize: 15, fontWeight: "900" },
  safetyButton: { minHeight: 38, borderRadius: 9, paddingHorizontal: 11, backgroundColor: stitch.blueSoft, flexDirection: "row", alignItems: "center", gap: 5 },
  safetyButtonText: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  policyNote: { color: stitch.outline, fontSize: 11, lineHeight: 17, fontWeight: "600" },
  errorBox: { padding: 13, borderRadius: 10, backgroundColor: stitch.redSoft, flexDirection: "row", alignItems: "flex-start", gap: 8 },
  errorText: { flex: 1, color: stitch.red, fontSize: 12, lineHeight: 18, fontWeight: "700" },
  anonymousNote: { color: stitch.outline, fontSize: 11, lineHeight: 17, fontWeight: "600", textAlign: "center" },
});