import { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import { fetchApi } from "@/lib/api";
import { t } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

interface CaseDetail {
  id: string;
  title: string;
  workplace_name: string | null;
  employer_name: string | null;
  status: string;
  created_at: string;
  // 분석 결과(있을 때)
  analysis?: {
    expected_wage?: number | null;
    received_wage?: number | null;
    suspected_unpaid?: number | null;
  } | null;
}

export default function CaseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [data, setData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchApi<CaseDetail>(`/cases/${id}`)
      .then(setData)
      .catch(() => setError("사건 정보를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [id]);

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

  const won = (n?: number | null) =>
    n == null ? "—" : `${n.toLocaleString("ko-KR")}원`;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{data.workplace_name || data.title}</Text>
      <Text style={styles.badge}>{data.status}</Text>

      <Section title={t("cases.workplace")}>
        <Row k={t("cases.employer")} v={data.employer_name || "—"} />
        <Row k={t("cases.status")} v={data.status} />
        <Row k="생성일" v={data.created_at?.slice(0, 10)} />
      </Section>

      <Section title={t("analysis.title")}>
        <Row k={t("analysis.expected")} v={won(data.analysis?.expected_wage)} />
        <Row k={t("analysis.received")} v={won(data.analysis?.received_wage)} />
        <Row
          k={t("analysis.suspected")}
          v={won(data.analysis?.suspected_unpaid)}
          highlight
        />
      </Section>

      <Text style={styles.disclaimer}>{t("disclaimer")}</Text>
    </ScrollView>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Row({
  k,
  v,
  highlight,
}: {
  k: string;
  v: string;
  highlight?: boolean;
}) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowK}>{k}</Text>
      <Text style={[styles.rowV, highlight && { color: colors.danger, fontWeight: "700" }]}>
        {v}
      </Text>
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
  rowV: { color: colors.text, fontSize: 14, fontWeight: "500" },
  disclaimer: {
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
    marginTop: spacing.md,
  },
});
