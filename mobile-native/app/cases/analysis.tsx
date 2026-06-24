import { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { fetchApi, ApiError, API_BASE } from "@/lib/api";
import type { AnalysisReport } from "@/lib/types";
import { t, i18n } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

const won = (n?: number | null) =>
  n == null ? "—" : `${n.toLocaleString("ko-KR")}원`;

export default function AnalysisScreen() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const fetchExisting = useCallback(async () => {
    try {
      const r = await fetchApi<AnalysisReport>(`/cases/${caseId}/analysis`);
      setReport(r);
    } catch (e) {
      // 분석 이력 없음(404 등)은 정상 — 실행 버튼 노출
      if (!(e instanceof ApiError)) {
        // network 등은 조용히 무시
      }
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchExisting();
  }, [fetchExisting]);

  async function runAnalyze() {
    setRunning(true);
    try {
      const r = await fetchApi<AnalysisReport>(
        `/cases/${caseId}/analyze?lang=${i18n.locale}`,
        { method: "POST", body: JSON.stringify({}) }
      );
      setReport(r);
    } catch (e: any) {
      Alert.alert("분석 실패", String(e?.message ?? e));
    } finally {
      setRunning(false);
    }
  }

  function openReport() {
    // 제출용 Evidence Pack — 백엔드 report.html(공개) 을 앱 내 브라우저로 연다.
    // (진짜 PDF 다운로드 엔드포인트 report.pdf 는 백엔드 연계 항목)
    WebBrowser.openBrowserAsync(
      `${API_BASE}/cases/${caseId}/report.html?lang=${i18n.locale}`
    ).catch(() => {});
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Pressable
        style={styles.run}
        onPress={runAnalyze}
        disabled={running}
      >
        {running ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.runText}>
            {report ? "다시 분석" : t("analysis.run")}
          </Text>
        )}
      </Pressable>

      {!report ? (
        <Text style={styles.muted}>
          아직 분석 결과가 없습니다. 증거를 업로드한 뒤 분석을 실행하세요.
        </Text>
      ) : (
        <>
          {!!report.narrative?.summary && (
            <View style={styles.summary}>
              <Text style={styles.summaryText}>{report.narrative.summary}</Text>
            </View>
          )}

          {/* 급여 차액 */}
          <Section title={t("analysis.title")}>
            <Row k={t("analysis.expected")} v={won(report.wage.expected)} />
            <Row k={t("analysis.received")} v={won(report.wage.received)} />
            <Row
              k={t("analysis.suspected")}
              v={won(report.wage.suspected_unpaid)}
              highlight
            />
            {!!report.wage.basis && (
              <Text style={styles.basis}>{report.wage.basis}</Text>
            )}
            {!report.wage.computable && (
              <Text style={styles.muted}>
                ※ 차액을 계산하기에 자료가 부족합니다(확인 필요).
              </Text>
            )}
          </Section>

          {/* 공제 */}
          {report.deductions.length > 0 && (
            <Section title={t("analysis.deductions")}>
              {report.deductions.map((d, i) => (
                <Row key={i} k={d.name} v={won(d.amount)} />
              ))}
            </Section>
          )}

          {/* 법정 점검 */}
          {report.legal?.findings?.length > 0 && (
            <Section title="법정 점검">
              {report.legal.findings.map((f, i) => (
                <View key={i} style={styles.finding}>
                  <Text style={[styles.sev, sevStyle(f.severity)]}>
                    {f.severity.toUpperCase()}
                  </Text>
                  <Text style={styles.findingMsg}>{f.message}</Text>
                </View>
              ))}
            </Section>
          )}

          {/* 타임라인 */}
          {report.timeline.length > 0 && (
            <Section title={t("analysis.timeline")}>
              {report.timeline.map((it, i) => (
                <View key={i} style={styles.tl}>
                  <Text style={styles.tlDate}>{it.date || "—"}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.tlText}>{it.text}</Text>
                    {!!it.text_translated && (
                      <Text style={styles.tlTrans}>{it.text_translated}</Text>
                    )}
                  </View>
                  {it.confidence === "low" && (
                    <Text style={styles.lowBadge}>확인 필요</Text>
                  )}
                </View>
              ))}
            </Section>
          )}

          {/* 추가 필요 증거 */}
          {report.missing.length > 0 && (
            <Section title={t("analysis.missing")}>
              {report.missing.map((m, i) => (
                <View key={i} style={{ paddingVertical: 4 }}>
                  <Text style={styles.tlText}>• {m.item}</Text>
                  <Text style={styles.muted}>{m.reason}</Text>
                </View>
              ))}
            </Section>
          )}
        </>
      )}

      {report && (
        <Pressable style={styles.report} onPress={openReport}>
          <Text style={styles.reportText}>📄 제출용 리포트(Evidence Pack) 보기</Text>
        </Pressable>
      )}

      <Text style={styles.disclaimer}>
        {report?.narrative?.disclaimer || t("disclaimer")}
      </Text>
    </ScrollView>
  );
}

function sevStyle(sev: string) {
  if (sev === "high") return { backgroundColor: "#fee2e2", color: colors.danger };
  if (sev === "medium") return { backgroundColor: "#fef3c7", color: "#b45309" };
  return { backgroundColor: colors.badge, color: colors.textMuted };
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Row({ k, v, highlight }: { k: string; v: string; highlight?: boolean }) {
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
  run: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
  },
  runText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  muted: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
  summary: {
    backgroundColor: "#eff6ff",
    borderRadius: radius.md,
    padding: spacing.md,
  },
  summaryText: { color: colors.text, lineHeight: 21 },
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
  row: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 4 },
  rowK: { color: colors.textMuted, fontSize: 14, flexShrink: 1 },
  rowV: { color: colors.text, fontSize: 14, fontWeight: "500" },
  basis: { color: colors.textMuted, fontSize: 12, marginTop: spacing.xs },
  finding: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: 4 },
  sev: {
    fontSize: 10,
    fontWeight: "700",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: radius.sm,
    overflow: "hidden",
  },
  findingMsg: { flex: 1, color: colors.text, fontSize: 13 },
  tl: { flexDirection: "row", gap: spacing.sm, paddingVertical: 6, alignItems: "flex-start" },
  tlDate: { color: colors.textMuted, fontSize: 12, width: 78 },
  tlText: { color: colors.text, fontSize: 14 },
  tlTrans: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  lowBadge: {
    fontSize: 10,
    color: "#b45309",
    backgroundColor: "#fef3c7",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: radius.sm,
    overflow: "hidden",
  },
  report: {
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
    backgroundColor: colors.card,
  },
  reportText: { color: colors.primary, fontWeight: "700", fontSize: 15 },
  disclaimer: {
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
    marginTop: spacing.md,
  },
});
