import { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Pressable,
} from "react-native";
import { useLocalSearchParams, useRouter, useFocusEffect } from "expo-router";
import { fetchApi } from "@/lib/api";
import type { Case, EvidenceItem } from "@/lib/types";
import { ISSUE_LABELS } from "@/lib/types";
import { t } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

export default function CaseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<Case | null>(null);
  const [evidences, setEvidences] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [c, evs] = await Promise.all([
        fetchApi<Case>(`/cases/${id}`),
        fetchApi<EvidenceItem[]>(`/cases/${id}/evidences`).catch(() => []),
      ]);
      setData(c);
      setEvidences(evs);
    } catch {
      setError("사건 정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  // 업로드/분석 화면에서 돌아올 때 갱신
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }
  if (error || !data) {
    return (
      <View style={styles.center}>
        <Text style={{ color: colors.textMuted }}>{error}</Text>
      </View>
    );
  }

  const period = [data.work_start_date, data.work_end_date]
    .map((d) => d || "—")
    .join(" ~ ");

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{data.workplace_name || "(무제 사건)"}</Text>
      <Text style={styles.badge}>{data.status}</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{t("cases.workplace")}</Text>
        <Row k={t("cases.employer")} v={data.employer_name || "—"} />
        <Row k={t("cases.period")} v={period} />
        <Row
          k={t("cases.wage")}
          v={
            data.agreed_hourly_wage != null
              ? `${data.agreed_hourly_wage.toLocaleString("ko-KR")}원`
              : "—"
          }
        />
        <Row
          k={t("cases.issueType")}
          v={
            data.issue_types.length
              ? data.issue_types.map((i) => ISSUE_LABELS[i] ?? i).join(", ")
              : "—"
          }
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>
          {t("upload.title")} ({evidences.length})
        </Text>
        {evidences.length === 0 ? (
          <Text style={styles.muted}>아직 업로드된 증거가 없습니다.</Text>
        ) : (
          evidences.map((e) => (
            <View key={e.id} style={styles.evRow}>
              <Text style={styles.evName} numberOfLines={1}>
                {e.file_name}
              </Text>
              <Text style={styles.evStatus}>{e.ocr_status || e.category}</Text>
            </View>
          ))
        )}
      </View>

      <Pressable
        style={styles.secondary}
        onPress={() =>
          router.push({ pathname: "/cases/upload", params: { caseId: id } })
        }
      >
        <Text style={styles.secondaryText}>+ {t("upload.title")}</Text>
      </Pressable>

      <Pressable
        style={styles.primary}
        onPress={() =>
          router.push({ pathname: "/cases/analysis", params: { caseId: id } })
        }
      >
        <Text style={styles.primaryText}>{t("analysis.title")}</Text>
      </Pressable>

      <Text style={styles.disclaimer}>{t("disclaimer")}</Text>
    </ScrollView>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowK}>{k}</Text>
      <Text style={styles.rowV}>{v}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.md },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  title: { fontSize: 22, fontWeight: "800", color: colors.text },
  badge: {
    alignSelf: "flex-start",
    backgroundColor: colors.badge,
    color: colors.textMuted,
    fontSize: 12,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.full,
    overflow: "hidden",
  },
  section: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.xs,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.primary,
    marginBottom: spacing.xs,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
  },
  rowK: { color: colors.textMuted, fontSize: 14 },
  rowV: { color: colors.text, fontSize: 14, fontWeight: "500", flexShrink: 1, textAlign: "right" },
  muted: { color: colors.textMuted, fontSize: 13 },
  evRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
  },
  evName: { color: colors.text, fontSize: 13, flex: 1, marginRight: spacing.sm },
  evStatus: { color: colors.textMuted, fontSize: 12 },
  primary: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
  },
  primaryText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  secondary: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
    backgroundColor: colors.card,
  },
  secondaryText: { color: colors.text, fontWeight: "600" },
  disclaimer: {
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
    marginTop: spacing.md,
  },
});
