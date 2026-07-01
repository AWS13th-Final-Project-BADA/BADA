import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { fetchApi } from "@/lib/api";
import type { Case, CaseCreate } from "@/lib/types";
import { ISSUE_LABELS, ISSUE_TYPES } from "@/lib/types";
import { Card, Chip, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

export default function NewCase() {
  const router = useRouter();
  const { locale } = useLocale();
  const params = useLocalSearchParams<{ editId?: string }>();
  const editId = params.editId || null;
  const isEdit = !!editId;
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<CaseCreate>({
    workplace_name: "",
    employer_name: "",
    work_start_date: "",
    work_end_date: "",
    agreed_hourly_wage: null,
    issue_types: [],
  });

  function set<K extends keyof CaseCreate>(key: K, value: CaseCreate[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleIssue(issue: string) {
    const current = form.issue_types ?? [];
    set("issue_types", current.includes(issue) ? current.filter((item) => item !== issue) : [...current, issue]);
  }

  // 편집 모드면 기존 사건 값을 불러와 폼을 채운다. (실패 시 빈 폼 유지 — 기존 동작 보존)
  useEffect(() => {
    if (!isEdit) return;
    let cancelled = false;
    fetchApi<Case>(`/cases/${editId}`)
      .then((c) => {
        if (cancelled || !c) return;
        setForm({
          workplace_name: c.workplace_name ?? "",
          employer_name: c.employer_name ?? "",
          work_start_date: c.work_start_date ?? "",
          work_end_date: c.work_end_date ?? "",
          agreed_hourly_wage: c.agreed_hourly_wage ?? null,
          issue_types: c.issue_types ?? [],
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [isEdit, editId]);

  async function submit() {
    if (busy) return;
    setBusy(true);
    try {
      const payload: CaseCreate = {
        workplace_name: form.workplace_name?.trim() || null,
        employer_name: form.employer_name?.trim() || null,
        work_start_date: form.work_start_date?.trim() || null,
        work_end_date: form.work_end_date?.trim() || null,
        agreed_hourly_wage: form.agreed_hourly_wage || null,
        issue_types: form.issue_types ?? [],
      };
      if (isEdit) {
        await fetchApi<Case>(`/cases/${editId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        router.back();
      } else {
        const created = await fetchApi<Case>("/cases", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        router.replace({ pathname: "/cases/[id]", params: { id: created.id } });
      }
    } catch (e: any) {
      Alert.alert("저장 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <StitchScreen active="cases">
      <TopBar title={isEdit ? t("cases.actions.edit") : t("cases.newTitle")} back />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View>
          <Text style={styles.title}>{t("cases.newTitle")}</Text>
          <Text style={styles.subtitle}>{t("cases.newSubtitle")}</Text>
        </View>

        <Card style={styles.formCard}>
          <Field label={t("cases.workplace")}>
            <TextInput
              style={styles.input}
              value={form.workplace_name ?? ""}
              onChangeText={(value) => set("workplace_name", value)}
              placeholder={t("cases.workplacePlaceholder")}
              placeholderTextColor={stitch.outline}
            />
          </Field>

          <Field label={t("cases.employer")}>
            <TextInput
              style={styles.input}
              value={form.employer_name ?? ""}
              onChangeText={(value) => set("employer_name", value)}
              placeholder={t("cases.employerPlaceholder")}
              placeholderTextColor={stitch.outline}
            />
          </Field>

          <View style={styles.rowFields}>
            <Field label={t("cases.startDate")} flex>
              <TextInput
                style={styles.input}
                value={form.work_start_date ?? ""}
                onChangeText={(value) => set("work_start_date", value)}
                placeholder="2026-05-01"
                placeholderTextColor={stitch.outline}
                autoCapitalize="none"
              />
            </Field>
            <Field label={t("cases.endDate")} flex>
              <TextInput
                style={styles.input}
                value={form.work_end_date ?? ""}
                onChangeText={(value) => set("work_end_date", value)}
                placeholder=""
                placeholderTextColor={stitch.outline}
                autoCapitalize="none"
              />
            </Field>
          </View>

          <Field label={t("cases.wage")}>
            <TextInput
              style={styles.input}
              value={form.agreed_hourly_wage ? String(form.agreed_hourly_wage) : ""}
              onChangeText={(value) =>
                set("agreed_hourly_wage", value ? parseInt(value.replace(/[^0-9]/g, ""), 10) : null)
              }
              placeholder="예: 10030"
              placeholderTextColor={stitch.outline}
              keyboardType="number-pad"
            />
          </Field>

          <Field label={t("cases.issueType")}>
            <View style={styles.chips}>
              {ISSUE_TYPES.map((issue) => {
                const active = (form.issue_types ?? []).includes(issue);
                return (
                  <Pressable key={issue} onPress={() => toggleIssue(issue)}>
                    <Chip label={t("cases.issueTypes." + issue)} active={active} />
                  </Pressable>
                );
              })}
            </View>
          </Field>
        </Card>

        <StitchButton icon="folder-open" onPress={submit} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : isEdit ? t("cases.actions.edit") : t("cases.create")}
        </StitchButton>

        <Card style={styles.note}>
          <Text style={styles.noteText}>{t("disclaimer")}</Text>
        </Card>
      </ScrollView>
    </StitchScreen>
  );
}

function Field({
  label,
  children,
  flex,
}: {
  label: string;
  children: React.ReactNode;
  flex?: boolean;
}) {
  return (
    <View style={[styles.field, flex && { flex: 1 }]}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 18, paddingBottom: 112 },
  title: { color: stitch.text, fontSize: 26, lineHeight: 34, fontWeight: "900" },
  subtitle: { marginTop: 6, color: stitch.muted, fontSize: 14, lineHeight: 21, fontWeight: "700" },
  formCard: { padding: 18, gap: 16 },
  field: { gap: 8 },
  rowFields: { flexDirection: "row", gap: 10 },
  label: { color: stitch.muted, fontSize: 12, fontWeight: "900" },
  input: { minHeight: 48, borderWidth: 1, borderColor: "rgba(198,198,205,0.65)", borderRadius: 8, paddingHorizontal: 12, backgroundColor: stitch.surface, color: stitch.text, fontSize: 15, fontWeight: "700" },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  note: { padding: 14, backgroundColor: stitch.surfaceLow },
  noteText: { color: stitch.muted, fontSize: 12, lineHeight: 18, fontWeight: "700" },
});
