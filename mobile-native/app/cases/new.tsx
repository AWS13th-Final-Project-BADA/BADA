import { useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { fetchApi } from "@/lib/api";
import type { Case, CaseCreate } from "@/lib/types";
import { ISSUE_LABELS, ISSUE_TYPES } from "@/lib/types";
import { Card, Chip, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";

export default function NewCase() {
  const router = useRouter();
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
      const created = await fetchApi<Case>("/cases", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.replace({ pathname: "/cases/[id]", params: { id: created.id } });
    } catch (e: any) {
      Alert.alert("저장 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <StitchScreen active="cases">
      <TopBar title="새 사건" back />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View>
          <Text style={styles.title}>사건 기본 정보를 입력하세요</Text>
          <Text style={styles.subtitle}>정확하지 않아도 괜찮아요. 지금 아는 내용부터 저장하고 나중에 보완할 수 있습니다.</Text>
        </View>

        <Card style={styles.formCard}>
          <Field label="사업장 이름">
            <TextInput
              style={styles.input}
              value={form.workplace_name ?? ""}
              onChangeText={(value) => set("workplace_name", value)}
              placeholder="예: 바다식품"
              placeholderTextColor={stitch.outline}
            />
          </Field>

          <Field label="사업주 또는 담당자">
            <TextInput
              style={styles.input}
              value={form.employer_name ?? ""}
              onChangeText={(value) => set("employer_name", value)}
              placeholder="예: 김대표"
              placeholderTextColor={stitch.outline}
            />
          </Field>

          <View style={styles.rowFields}>
            <Field label="근무 시작일" flex>
              <TextInput
                style={styles.input}
                value={form.work_start_date ?? ""}
                onChangeText={(value) => set("work_start_date", value)}
                placeholder="2026-05-01"
                placeholderTextColor={stitch.outline}
                autoCapitalize="none"
              />
            </Field>
            <Field label="근무 종료일" flex>
              <TextInput
                style={styles.input}
                value={form.work_end_date ?? ""}
                onChangeText={(value) => set("work_end_date", value)}
                placeholder="근무 중이면 비워두기"
                placeholderTextColor={stitch.outline}
                autoCapitalize="none"
              />
            </Field>
          </View>

          <Field label="약속한 시급">
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

          <Field label="상담 주제">
            <View style={styles.chips}>
              {ISSUE_TYPES.map((issue) => {
                const active = (form.issue_types ?? []).includes(issue);
                return (
                  <Pressable key={issue} onPress={() => toggleIssue(issue)}>
                    <Chip label={ISSUE_LABELS[issue]} active={active} />
                  </Pressable>
                );
              })}
            </View>
          </Field>
        </Card>

        <StitchButton icon="folder-open" onPress={submit} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : "사건 저장하기"}
        </StitchButton>

        <Card style={styles.note}>
          <Text style={styles.noteText}>BADA는 법률 판단을 하지 않습니다. 입력한 정보는 상담 준비용 사건 파일을 만드는 데 사용됩니다.</Text>
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
