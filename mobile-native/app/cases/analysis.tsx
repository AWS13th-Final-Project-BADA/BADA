import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { fetchApi } from "@/lib/api";
import type { AnalysisReport, MissingItem, TimelineItem } from "@/lib/types";
import { Card, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

const won = (n?: number | null) =>
  n == null ? t("analysis.suspected") : `${Math.round(n).toLocaleString("ko-KR")}원`;

export default function AnalysisScreen() {
  const { caseId = "demo-case-1" } = useLocalSearchParams<{ caseId?: string }>();
  const router = useRouter();
  const { locale } = useLocale();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetchApi<AnalysisReport>(`/cases/${caseId}/analysis`)
      .then(setReport)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [caseId]);

  async function runAnalyze() {
    setRunning(true);
    try {
      const next = await fetchApi<AnalysisReport>(`/cases/${caseId}/analyze?lang=ko`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setReport(next);
    } finally {
      setRunning(false);
    }
  }

  const expected = report?.wage?.expected ?? 2300000;
  const received = report?.wage?.received ?? 1900000;
  const diff = report?.wage?.suspected_unpaid ?? 400000;
  const timeline = report?.timeline?.length ? report.timeline : defaultTimeline;
  const missing = report?.missing?.length ? report.missing : defaultMissing;

  return (
    <StitchScreen active="assistant">
      <TopBar title={t("analysis.title")} back />
      <View style={styles.content}>
        <View>
          <Text style={styles.screenTitle}>{t("analysis.title")}</Text>
          <Text style={styles.caseId}>Case #{String(caseId).slice(0, 8)}</Text>
        </View>

        {loading ? <ActivityIndicator color={stitch.blue} /> : null}

        <Card style={styles.summary}>
          <View style={styles.summaryTop}>
            <Text style={styles.summaryTitle}>{t("analysis.title")}</Text>
            <Text style={styles.badge}>자료 기준</Text>
          </View>
          <Text style={styles.summaryBody}>
            {report?.narrative?.summary ||
              "업로드한 급여명세서, 입금내역, 계약서를 기준으로 상담 전에 확인할 쟁점을 정리했습니다."}
          </Text>
          <View style={styles.infoStrip}>
            <MaterialIcons name="info-outline" size={20} color={stitch.blue} />
            <Text style={styles.infoText}>{t("analysis.suspected")}: {won(diff)}</Text>
          </View>
        </Card>

        <View style={styles.grid}>
          <AmountCard label={t("analysis.expected")} value={won(expected)} progress={1} color={stitch.navy} />
          <AmountCard label={t("analysis.received")} value={won(received)} progress={0.82} color={stitch.blue} />
        </View>

        <View style={styles.twoCol}>
          <Card style={styles.foundCard}>
            <SectionTitle icon="check-circle" title={t("analysis.title")} color={stitch.green} />
            <CheckRow text={t("upload.categories.statement")} />
            <CheckRow text={t("upload.categories.payment")} />
            <CheckRow text={t("upload.categories.contract")} />
          </Card>

          <Card style={styles.missingCard}>
            <SectionTitle icon="pending" title="부족한 자료" color={stitch.outline} />
            {missing.slice(0, 2).map((item) => (
              <View key={item.item} style={styles.missingItem}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.missingTitle}>{item.item}</Text>
                  <Text style={styles.missingBody}>{item.reason}</Text>
                </View>
                <Text style={styles.needCheck}>확인 필요</Text>
              </View>
            ))}
          </Card>
        </View>

        <View style={styles.sectionBlock}>
          <Text style={styles.sectionLabel}>{t("analysis.timeline")}</Text>
          <Card style={styles.timelineCard}>
            {timeline.slice(0, 3).map((item, index) => (
              <Timeline key={`${item.date}-${index}`} item={item} active={index === 0} />
            ))}
          </Card>
        </View>

        <Card style={styles.questionCard}>
          <View style={styles.questionHeader}>
            <MaterialIcons name="smart-toy" size={22} color={stitch.blue} />
            <Text style={styles.questionTitle}>{t("chat.emptyTitle")}</Text>
          </View>
          <Question text="급여명세서와 실제 입금액 차이를 어떤 순서로 설명하면 좋을까요?" />
          <Question text="공제 항목은 어떤 자료로 확인받아야 하나요?" />
          <Question text="근무시간 기록이 부족할 때 대신 준비할 수 있는 자료가 있나요?" />
        </Card>

        <Card style={styles.disclaimer}>
          <MaterialIcons name="gavel" size={22} color={stitch.outline} />
          <Text style={styles.disclaimerText}>
            {report?.narrative?.disclaimer ||
              "BADA는 법률 판단을 하지 않습니다. 이 결과는 상담 전 자료 정리 안내이며, 최종 판단은 고용노동부 또는 상담기관에서 확인해야 합니다."}
          </Text>
        </Card>

        <StitchButton icon="analytics" onPress={runAnalyze} disabled={running}>
          {running ? t("common.loading") : report ? t("cases.actions.rerun") : t("cases.runAnalysis")}
        </StitchButton>
        <StitchButton tone="secondary" onPress={() => router.push({ pathname: "/chat", params: { caseId } })}>
          <Text style={styles.secondaryButton}>{t("cases.actions.chatBody")}</Text>
        </StitchButton>
      </View>
    </StitchScreen>
  );
}

function AmountCard({
  label,
  value,
  progress,
  color,
}: {
  label: string;
  value: string;
  progress: number;
  color: string;
}) {
  return (
    <Card style={styles.amountCard}>
      <Text style={styles.amountLabel}>{label}</Text>
      <Text style={styles.amountValue}>{value}</Text>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${Math.round(progress * 100)}%`, backgroundColor: color }]} />
      </View>
    </Card>
  );
}

function SectionTitle({
  icon,
  title,
  color,
}: {
  icon: keyof typeof MaterialIcons.glyphMap;
  title: string;
  color: string;
}) {
  return (
    <View style={styles.sectionTitleRow}>
      <MaterialIcons name={icon} size={22} color={color} />
      <Text style={[styles.cardTitle, { color }]}>{title}</Text>
    </View>
  );
}

function CheckRow({ text }: { text: string }) {
  return (
    <View style={styles.checkRow}>
      <Text style={styles.checkText}>{text}</Text>
      <MaterialIcons name="verified" size={20} color={stitch.green} />
    </View>
  );
}

function Timeline({ item, active }: { item: TimelineItem; active?: boolean }) {
  return (
    <View style={styles.timeline}>
      <View style={styles.timelineRail}>
        <View style={[styles.timelineDot, active && styles.timelineDotOn]} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={[styles.timelineDate, active && styles.timelineDateOn]}>{item.date || "날짜 미확인"}</Text>
        <Text style={styles.timelineTitle}>{item.type === "payment" ? "입금 자료 확인" : "자료 확인"}</Text>
        <Text style={styles.timelineBody}>{item.text}</Text>
      </View>
    </View>
  );
}

function Question({ text }: { text: string }) {
  return (
    <Pressable style={styles.question}>
      <Text style={styles.questionText}>{text}</Text>
      <MaterialIcons name="chevron-right" size={20} color={stitch.blue} />
    </Pressable>
  );
}

const defaultTimeline: TimelineItem[] = [
  {
    date: "2026-05-31",
    type: "payment",
    text: "5월 급여 입금액 1,900,000원이 확인되었습니다.",
    text_translated: null,
    source_evidence_id: null,
    confidence: "high",
  },
  {
    date: "2026-06-01",
    type: "document",
    text: "급여명세서상 지급액 2,300,000원이 확인되었습니다.",
    text_translated: null,
    source_evidence_id: null,
    confidence: "high",
  },
];

const defaultMissing: MissingItem[] = [
  { item: "근무시간 기록", reason: "약속 임금과 실제 근무시간 비교에 필요합니다." },
  { item: "공제 동의 자료", reason: "공제 항목이 설명되었는지 확인하는 데 필요합니다." },
];

const styles = StyleSheet.create({
  content: { padding: 20, gap: 16 },
  screenTitle: { color: stitch.text, fontSize: 28, lineHeight: 36, fontWeight: "900" },
  caseId: { marginTop: 4, color: stitch.outline, fontSize: 13, fontWeight: "800" },
  summary: { padding: 20, gap: 14 },
  summaryTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  summaryTitle: { color: stitch.text, fontSize: 20, lineHeight: 28, fontWeight: "900" },
  badge: { color: stitch.blue, backgroundColor: "rgba(0,81,213,0.1)", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, overflow: "hidden", fontSize: 12, fontWeight: "900" },
  summaryBody: { color: stitch.muted, fontSize: 14, lineHeight: 22, fontWeight: "600" },
  infoStrip: { flexDirection: "row", alignItems: "center", gap: 8, padding: 12, backgroundColor: stitch.surfaceLow, borderLeftWidth: 4, borderLeftColor: stitch.blue, borderRadius: 8 },
  infoText: { color: stitch.text, fontSize: 13, fontWeight: "900" },
  grid: { flexDirection: "row", gap: 12 },
  amountCard: { flex: 1, padding: 16, gap: 8 },
  amountLabel: { color: stitch.outline, fontSize: 11, fontWeight: "900" },
  amountValue: { color: stitch.text, fontSize: 18, fontWeight: "900" },
  progressTrack: { height: 4, borderRadius: 999, backgroundColor: stitch.surfaceHigh, overflow: "hidden" },
  progressFill: { height: "100%", borderRadius: 999 },
  twoCol: { gap: 12 },
  foundCard: { padding: 16, gap: 12, backgroundColor: "rgba(0,150,104,0.05)", borderColor: "rgba(0,150,104,0.22)" },
  missingCard: { padding: 16, gap: 12, backgroundColor: "rgba(230,232,234,0.55)" },
  sectionTitleRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardTitle: { fontSize: 14, fontWeight: "900" },
  checkRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 3 },
  checkText: { color: stitch.text, fontSize: 14, fontWeight: "700" },
  missingItem: { flexDirection: "row", gap: 10, alignItems: "center" },
  missingTitle: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  missingBody: { color: stitch.muted, fontSize: 12, lineHeight: 18, marginTop: 2 },
  needCheck: { color: stitch.muted, backgroundColor: stitch.surfaceHigh, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 5, overflow: "hidden", fontSize: 11, fontWeight: "900" },
  sectionBlock: { gap: 10 },
  sectionLabel: { color: stitch.outline, fontSize: 12, fontWeight: "900" },
  timelineCard: { padding: 16, gap: 16 },
  timeline: { flexDirection: "row", gap: 12 },
  timelineRail: { width: 16, alignItems: "center" },
  timelineDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: stitch.line, marginTop: 3 },
  timelineDotOn: { backgroundColor: stitch.blue },
  timelineDate: { color: stitch.outline, fontSize: 12, fontWeight: "900" },
  timelineDateOn: { color: stitch.blue },
  timelineTitle: { color: stitch.text, fontSize: 14, fontWeight: "900", marginTop: 2 },
  timelineBody: { color: stitch.muted, fontSize: 13, lineHeight: 19, marginTop: 2 },
  questionCard: { padding: 16, gap: 10, backgroundColor: "#131b2e" },
  questionHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  questionTitle: { color: "#fff", fontSize: 18, fontWeight: "900" },
  question: { minHeight: 48, borderRadius: 8, backgroundColor: "rgba(255,255,255,0.08)", paddingHorizontal: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  questionText: { flex: 1, color: "#fff", fontSize: 13, lineHeight: 19, fontWeight: "700" },
  disclaimer: { padding: 14, flexDirection: "row", gap: 10, backgroundColor: stitch.surfaceLow },
  disclaimerText: { flex: 1, color: stitch.muted, fontSize: 12, lineHeight: 18, fontWeight: "700" },
  secondaryButton: { color: stitch.text, fontWeight: "900", fontSize: 15 },
});
