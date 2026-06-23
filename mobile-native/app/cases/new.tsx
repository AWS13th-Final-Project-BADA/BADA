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
import type { Case, CaseCreate } from "@/lib/types";
import { ISSUE_TYPES, ISSUE_LABELS } from "@/lib/types";
import { t } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

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

  function set<K extends keyof CaseCreate>(k: K, v: CaseCreate[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function toggleIssue(issue: string) {
    const cur = form.issue_types ?? [];
    set(
      "issue_types",
      cur.includes(issue) ? cur.filter((i) => i !== issue) : [...cur, issue]
    );
  }

  async function submit() {
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
    <ScrollView contentContainerStyle={styles.container}>
      <Field label={t("cases.workplace")}>
        <TextInput
          style={styles.input}
          value={form.workplace_name ?? ""}
          onChangeText={(v) => set("workplace_name", v)}
          placeholder="예: ○○물산"
        />
      </Field>

      <Field label={t("cases.employer")}>
        <TextInput
          style={styles.input}
          value={form.employer_name ?? ""}
          onChangeText={(v) => set("employer_name", v)}
          placeholder="예: 홍길동 사장"
        />
      </Field>

      <View style={styles.rowFields}>
        <Field label="근무 시작 (YYYY-MM-DD)" flex>
          <TextInput
            style={styles.input}
            value={form.work_start_date ?? ""}
            onChangeText={(v) => set("work_start_date", v)}
            placeholder="2025-01-01"
            autoCapitalize="none"
          />
        </Field>
        <Field label="근무 종료" flex>
          <TextInput
            style={styles.input}
            value={form.work_end_date ?? ""}
            onChangeText={(v) => set("work_end_date", v)}
            placeholder="진행중이면 비움"
            autoCapitalize="none"
          />
        </Field>
      </View>

      <Field label={t("cases.wage")}>
        <TextInput
          style={styles.input}
          value={form.agreed_hourly_wage ? String(form.agreed_hourly_wage) : ""}
          onChangeText={(v) =>
            set("agreed_hourly_wage", v ? parseInt(v.replace(/[^0-9]/g, ""), 10) : null)
          }
          placeholder="예: 9860"
          keyboardType="number-pad"
        />
      </Field>

      <Field label={t("cases.issueType")}>
        <View style={styles.chips}>
          {ISSUE_TYPES.map((issue) => {
            const on = (form.issue_types ?? []).includes(issue);
            return (
              <Pressable
                key={issue}
                style={[styles.chip, on && styles.chipOn]}
                onPress={() => toggleIssue(issue)}
              >
                <Text style={[styles.chipText, on && styles.chipTextOn]}>
                  {ISSUE_LABELS[issue]}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </Field>

      <Pressable style={styles.submit} onPress={submit} disabled={busy}>
        {busy ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.submitText}>{t("common.save")}</Text>
        )}
      </Pressable>

      <Text style={styles.disclaimer}>{t("disclaimer")}</Text>
    </ScrollView>
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
  container: { padding: spacing.lg, gap: spacing.md },
  field: { gap: spacing.xs },
  rowFields: { flexDirection: "row", gap: spacing.sm },
  label: { fontSize: 13, color: colors.textMuted, fontWeight: "600" },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: spacing.sm,
    backgroundColor: "#fff",
    fontSize: 15,
  },
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
  submit: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
    marginTop: spacing.sm,
  },
  submitText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  disclaimer: {
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
    marginTop: spacing.md,
  },
});
