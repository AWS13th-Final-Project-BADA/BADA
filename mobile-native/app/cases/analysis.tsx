import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
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
  const [evidenceCount, setEvidenceCount] = useState<number | null>(null);
  const [evidences, setEvidences] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [needsRerun, setNeedsRerun] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    Promise.all([
      fetchApi<AnalysisReport>(`/cases/${caseId}/analysis`).catch((e) => {
        if (e?.status === 409) return "NEEDS_RERUN";
        return null;
      }),
      fetchApi<any[]>(`/cases/${caseId}/evidences`).catch(() => []),
    ]).then(([analysisData, evidences]) => {
      if (analysisData && analysisData !== "NEEDS_RERUN") {
        setReport(analysisData as AnalysisReport);
        scrollRef.current?.scrollTo({ y: 0, animated: true });
      } else if (analysisData === "NEEDS_RERUN") {
        setNeedsRerun(true);
      }
      setEvidenceCount(Array.isArray(evidences) ? evidences.length : 0);
      setEvidences(Array.isArray(evidences) ? evidences : []);
    }).finally(() => setLoading(false));
  }, [caseId]);

  async function runAnalyze() {
    setRunning(true);
    try {
      const next = await fetchApi<AnalysisReport>(`/cases/${caseId}/analyze?lang=ko`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setReport(next);
      scrollRef.current?.scrollTo({ y: 0, animated: true });
    } finally {
      setRunning(false);
    }
  }

  const expected = report?.wage?.expected;
  const received = report?.wage?.received;
  const diff = report?.wage?.suspected_unpaid;
  const timeline = report?.timeline?.length ? report.timeline : [];
  const missing = report?.missing?.length ? report.missing : [];

  return (
    <StitchScreen active="assistant" scroll={false}>
      <TopBar title={report ? t("analysis.title") : t("cases.uploadHistory")} back />

      {(loading || running) && (
        <View style={styles.loadingOverlay}>
          <View style={styles.loadingModal}>
            <ActivityIndicator size="large" color={stitch.blue} />
            <Text style={styles.loadingModalTitle}>{running ? t("cases.runAnalysis") : t("common.loading")}</Text>
            <Text style={styles.loadingModalBody}>{t("analysis.noneBody")}</Text>
          </View>
        </View>
      )}

      <ScrollView ref={scrollRef} showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
        <View>
          <Text style={styles.screenTitle}>{report ? t("analysis.title") : t("cases.uploadHistory")}</Text>
          <Text style={styles.caseId}>Case #{String(caseId).slice(0, 8)}</Text>
        </View>

        {!loading && !report ? (
          <>
            {needsRerun ? (
              <Card style={styles.emptyAnalysis}>
                <MaterialIcons name="refresh" size={48} color={stitch.blue} />
                <Text style={styles.emptyAnalysisTitle}>{t("cases.actions.rerun")}</Text>
                <Text style={styles.emptyAnalysisBody}>{t("cases.actions.rerunBody")}</Text>
                <View style={styles.emptyButtonWrap}>
                  <StitchButton tone="secondary" icon="upload-file" onPress={() => router.push({ pathname: "/cases/upload", params: { caseId } })}>
                    {t("cases.actions.addMore")}
                  </StitchButton>
                  <StitchButton icon="analytics" onPress={runAnalyze} disabled={running}>
                    {t("cases.runAnalysis")}
                  </StitchButton>
                </View>
              </Card>
            ) : evidenceCount === 0 ? (
              <Card style={styles.emptyAnalysis}>
                <MaterialIcons name="cloud-upload" size={48} color={stitch.outline} />
                <Text style={styles.emptyAnalysisTitle}>{t("analysis.needUpload")}</Text>
                <Text style={styles.emptyAnalysisBody}>{t("analysis.noneBody")}</Text>
                <View style={styles.emptyButtonWrap}>
                  <StitchButton icon="upload-file" onPress={() => router.push({ pathname: "/cases/upload", params: { caseId } })}>
                    {t("cases.upload")}
                  </StitchButton>
                </View>
              </Card>
            ) : (
              <Card style={styles.emptyAnalysis}>
                <MaterialIcons name="analytics" size={48} color={stitch.blue} />
                <Text style={styles.emptyAnalysisTitle}>{t("analysis.none")}</Text>
                <Text style={styles.emptyAnalysisBody}>{t("analysis.noneBody")}</Text>
                <View style={styles.emptyButtonWrap}>
                  <StitchButton tone="secondary" icon="upload-file" onPress={() => router.push({ pathname: "/cases/upload", params: { caseId } })}>
                    {t("cases.actions.addMore")}
                  </StitchButton>
                  <StitchButton icon="analytics" onPress={runAnalyze} disabled={running}>
                    {t("cases.runAnalysis")}
                  </StitchButton>
                </View>
              </Card>
            )}

            {evidences.length > 0 && (
              <Card style={styles.evidenceListCard}>
                <Text style={styles.evidenceListTitle}>{t("upload.currentFiles")} ({evidences.length})</Text>
                {evidences.map((item, index) => (
                  <View key={item.id || index} style={[styles.evidenceRow, index < evidences.length - 1 && styles.evidenceDivider]}>
                    <MaterialIcons name="description" size={20} color={stitch.blue} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.evidenceName} numberOfLines={1}>{item.file_name || item.original_filename || `파일 ${index + 1}`}</Text>
                      <Text style={styles.evidenceCategory}>{item.category ? t("upload.categories." + item.category) : ""}</Text>
                    </View>
                    <MaterialIcons name="check-circle" size={18} color={stitch.green} />
                  </View>
                ))}
              </Card>
            )}
          </>
        ) : null}

        {report ? (
          <>
            <Card style={styles.summary}>
              <View style={styles.summaryTop}>
                <Text style={styles.summaryTitle}>{t("analysis.preAnalysis")}</Text>
                <Text style={styles.badge}>{t("analysis.title")}</Text>
              </View>
              <View style={styles.summaryBodyWrap}>
                {(report.narrative?.summary || t("analysis.noneBody"))
                  .split(/\n|(?<=\.)\s+/)
                  .filter((p: string) => p.trim())
                  .map((paragraph: string, i: number) => (
                    <Text key={i} style={styles.summaryBody}>{paragraph.trim()}</Text>
                  ))}
              </View>
              <View style={styles.infoStrip}>
                <MaterialIcons name="info-outline" size={20} color={stitch.blue} />
                <Text style={styles.infoText}>{t("analysis.suspected")}: {won(report.wage?.suspected_unpaid)}</Text>
              </View>
            </Card>

            <View style={styles.grid}>
              <AmountCard label={t("analysis.expected")} value={won(report.wage?.expected)} progress={1} color={stitch.navy} />
              <AmountCard label={t("analysis.received")} value={won(report.wage?.received)} progress={0.82} color={stitch.blue} />
            </View>

            <View style={styles.twoCol}>
              <Card style={styles.foundCard}>
                <SectionTitle icon="check-circle" title={t("analysis.title")} color={stitch.green} />
                <CheckRow text={t("upload.categories.statement")} />
                <CheckRow text={t("upload.categories.payment")} />
                <CheckRow text={t("upload.categories.contract")} />
              </Card>

              <Card style={styles.missingCard}>
                <SectionTitle icon="pending" title={t("analysis.missing")} color={stitch.outline} />
                {(report.missing || []).slice(0, 2).map((item) => (
                  <View key={item.item} style={styles.missingItem}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.missingTitle}>{item.item}</Text>
                      <Text style={styles.missingBody}>{item.reason}</Text>
                    </View>
                    <Text style={styles.needCheck}>{t("analysis.suspected")}</Text>
                  </View>
                ))}
              </Card>
            </View>

            <View style={styles.sectionBlock}>
              <Text style={styles.sectionLabel}>{t("analysis.timeline")}</Text>
              <Card style={styles.timelineCard}>
                {(report.timeline || []).slice(0, 3).map((item, index) => (
                  <Timeline key={`${item.date}-${index}`} item={item} active={index === 0} />
                ))}
              </Card>
            </View>
          </>
        ) : null}

        <Card style={styles.disclaimer}>
          <MaterialIcons name="gavel" size={22} color={stitch.outline} />
          <Text style={styles.disclaimerText}>{t("disclaimer")}</Text>
        </Card>

        {report && (
          <StitchButton icon="picture-as-pdf" onPress={() => {
            const url = `https://api.badasoft.com/cases/${caseId}/report/pdf`;
            import("expo-linking").then((Linking) => Linking.openURL(url));
          }}>
            {t("analysis.download")}
          </StitchButton>
        )}

        <StitchButton tone="secondary" onPress={() => router.push({ pathname: "/chat", params: { caseId } })}>
          <Text style={styles.secondaryButton}>{t("cases.actions.chatBody")}</Text>
        </StitchButton>
      </ScrollView>
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
  content: { padding: 20, gap: 16, paddingBottom: 112 },
  screenTitle: { color: stitch.text, fontSize: 28, lineHeight: 36, fontWeight: "900" },
  caseId: { marginTop: 4, color: stitch.outline, fontSize: 13, fontWeight: "800" },
  summary: { padding: 20, gap: 14 },
  summaryTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  summaryTitle: { color: stitch.text, fontSize: 20, lineHeight: 28, fontWeight: "900" },
  badge: { color: stitch.blue, backgroundColor: "rgba(0,81,213,0.1)", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, overflow: "hidden", fontSize: 12, fontWeight: "900" },
  summaryBody: { color: stitch.muted, fontSize: 14, lineHeight: 22, fontWeight: "600" },
  summaryBodyWrap: { gap: 10 },
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
  loadingOverlay: { ...StyleSheet.absoluteFillObject, zIndex: 100, backgroundColor: "rgba(0,0,0,0.5)", alignItems: "center", justifyContent: "center" },
  loadingModal: { backgroundColor: stitch.surface, borderRadius: 16, padding: 32, alignItems: "center", gap: 12, minWidth: 240, shadowColor: "#000", shadowOpacity: 0.2, shadowRadius: 16, elevation: 10 },
  loadingModalTitle: { color: stitch.text, fontSize: 18, fontWeight: "900", marginTop: 8 },
  loadingModalBody: { color: stitch.muted, fontSize: 13, fontWeight: "700", textAlign: "center", lineHeight: 19 },
  emptyAnalysis: { padding: 32, alignItems: "center", gap: 14, paddingHorizontal: 24 },
  emptyAnalysisTitle: { color: stitch.text, fontSize: 18, fontWeight: "900", textAlign: "center" },
  emptyAnalysisBody: { color: stitch.muted, fontSize: 14, fontWeight: "700", textAlign: "center", lineHeight: 20, marginBottom: 8 },
  emptyButtonWrap: { width: "100%", paddingHorizontal: 16, gap: 10 },
  evidenceListCard: { padding: 16, gap: 0 },
  evidenceListTitle: { color: stitch.text, fontSize: 16, fontWeight: "900", marginBottom: 12 },
  evidenceRow: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 10 },
  evidenceDivider: { borderBottomWidth: 1, borderBottomColor: "rgba(198,198,205,0.28)" },
  evidenceName: { color: stitch.text, fontSize: 14, fontWeight: "700" },
  evidenceCategory: { color: stitch.outline, fontSize: 12, fontWeight: "700", marginTop: 2 },
});
