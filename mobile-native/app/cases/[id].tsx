import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { fetchApi } from "@/lib/api";
import type { Case, EvidenceItem } from "@/lib/types";
import { Card, StitchScreen, TopBar, stitch } from "@/components/StitchKit";

export default function CaseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<Case | null>(null);
  const [evidences, setEvidences] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [caseData, evidenceData] = await Promise.all([
        fetchApi<Case>(`/cases/${id}`),
        fetchApi<EvidenceItem[]>(`/cases/${id}/evidences`).catch(() => []),
      ]);
      setData(caseData);
      setEvidences(evidenceData);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  if (loading) {
    return <StitchScreen><TopBar title="BADA" back /><ActivityIndicator color={stitch.blue} style={{ marginTop: 80 }} /></StitchScreen>;
  }

  const title = data?.workplace_name || data?.employer_name || "Employment Contract Verification";
  const doneCount = evidences.filter((item) => item.ocr_status === "done" || item.ocr_status === "completed").length;
  const readiness = Math.min(100, 40 + evidences.length * 15 + doneCount * 10);

  return (
    <StitchScreen active="cases">
      <TopBar title="BADA" back />
      <View style={styles.content}>
        <View style={styles.caseHead}>
          <Text style={styles.caseId}>Case #{String(id || "8821").slice(0, 4)}</Text>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.status}>Status: <Text style={styles.statusStrong}>Under Review</Text> · Created 2026.06.24</Text>
        </View>

        <View style={styles.actionRow}>
          <Action icon="analytics" label="분석 실행" onPress={() => router.push({ pathname: "/cases/analysis", params: { caseId: id } })} />
          <Action icon="folder-zip" label="Evidence Pack" onPress={() => router.push({ pathname: "/cases/analysis", params: { caseId: id } })} />
        </View>

        <Card style={styles.readiness}>
          <View style={styles.readinessTop}>
            <View style={styles.readinessIcon}><MaterialIcons name="verified-user" size={24} color={stitch.blue} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.readinessLabel}>Readiness module</Text>
              <Text style={styles.readinessBody}>제출 준비가 거의 완료되었습니다. 누락 자료를 올리면 신뢰도가 더 높아집니다.</Text>
            </View>
            <Text style={styles.percent}>{readiness}%</Text>
          </View>
          <View style={styles.progressTrack}><View style={[styles.progressFill, { width: `${readiness}%` }]} /></View>
        </Card>

        <Section title="Evidence checklist" action="Upload more" onAction={() => router.push({ pathname: "/cases/upload", params: { caseId: id } })}>
          <EvidenceRow ok title="근로계약서" body="Verified on 2026.06.24" />
          <EvidenceRow ok={doneCount > 0} title="최근 급여명세서" body={doneCount > 0 ? "Uploaded yesterday" : "업로드 필요"} />
          <EvidenceRow warning title="4대보험 또는 출퇴근 기록" body="Mandatory document missing" />
        </Section>

        <Card style={styles.warningCard}>
          <View style={styles.warningIcon}><MaterialIcons name="priority-high" size={22} color={stitch.red} /></View>
          <View style={{ flex: 1 }}>
            <Text style={styles.warningTitle}>Critical Missing Information</Text>
            <Text style={styles.warningText}>신분증 사본, 최근 6개월 입금내역, 공제 설명 자료</Text>
          </View>
        </Card>

        <Pressable style={styles.aiCard} onPress={() => router.push({ pathname: "/chat", params: { caseId: id } })}>
          <View style={styles.aiIcon}><MaterialIcons name="smart-toy" size={26} color={stitch.blue} /></View>
          <View style={{ flex: 1 }}>
            <Text style={styles.aiTitle}>BADA AI Assistant</Text>
            <Text style={styles.aiBody}>계약서와 증거자료에 대해 상담 전 질문을 정리하세요.</Text>
          </View>
          <Text style={styles.aiButton}>Open AI Chatbot</Text>
        </Pressable>

        <Section title="Timeline">
          <Timeline icon="history-edu" title="Analysis Completed" time="Today, 2:15 PM" body="AI가 3개 문서를 스캔하고 확인이 필요한 항목 1개를 찾았습니다." />
          <Timeline icon="cloud-upload" title="급여명세서 업로드" time="Yesterday, 10:45 AM" body="급여명세서 PDF가 사건 폴더에 추가되었습니다." />
          <Timeline icon="description" title="Case Created" time="2026.06.24" body="상담 준비 사건이 생성되었습니다." />
        </Section>
      </View>
    </StitchScreen>
  );
}

function Action({ icon, label, onPress }: { icon: keyof typeof MaterialIcons.glyphMap; label: string; onPress: () => void }) {
  return <Pressable style={styles.action} onPress={onPress}><MaterialIcons name={icon} size={22} color="#fff" /><Text style={styles.actionText}>{label}</Text></Pressable>;
}

function Section({ title, action, onAction, children }: { title: string; action?: string; onAction?: () => void; children: React.ReactNode }) {
  return <Card style={styles.section}><View style={styles.sectionHead}><Text style={styles.sectionTitle}>{title}</Text>{action ? <Pressable onPress={onAction}><Text style={styles.sectionAction}>{action}</Text></Pressable> : null}</View>{children}</Card>;
}

function EvidenceRow({ ok, warning, title, body }: { ok?: boolean; warning?: boolean; title: string; body: string }) {
  return <View style={styles.evidenceRow}><MaterialIcons name={ok ? "check-circle" : warning ? "warning" : "radio-button-unchecked"} size={24} color={ok ? stitch.green : warning ? stitch.amber : stitch.outline} /><View style={{ flex: 1 }}><Text style={styles.evidenceTitle}>{title}</Text><Text style={styles.evidenceBody}>{body}</Text></View><MaterialIcons name="more-vert" size={22} color={stitch.outline} /></View>;
}

function Timeline({ icon, title, time, body }: { icon: keyof typeof MaterialIcons.glyphMap; title: string; time: string; body: string }) {
  return <View style={styles.timeline}><View style={styles.timelineIcon}><MaterialIcons name={icon} size={20} color={stitch.blue} /></View><View style={{ flex: 1 }}><Text style={styles.timelineTitle}>{title}</Text><Text style={styles.timelineTime}>{time}</Text><Text style={styles.timelineBody}>{body}</Text></View></View>;
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 16 },
  caseHead: { gap: 4 },
  caseId: { color: stitch.outline, fontSize: 12, fontWeight: "800" },
  title: { color: stitch.text, fontSize: 24, lineHeight: 32, fontWeight: "900" },
  status: { color: stitch.muted, fontSize: 13, lineHeight: 20 },
  statusStrong: { color: stitch.text, fontWeight: "900" },
  actionRow: { flexDirection: "row", gap: 12 },
  action: { flex: 1, height: 52, borderRadius: 8, backgroundColor: stitch.navy, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 8 },
  actionText: { color: "#fff", fontSize: 14, fontWeight: "900" },
  readiness: { padding: 16 },
  readinessTop: { flexDirection: "row", alignItems: "center", gap: 12 },
  readinessIcon: { width: 42, height: 42, borderRadius: 21, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  readinessLabel: { color: stitch.text, fontSize: 16, fontWeight: "900" },
  readinessBody: { color: stitch.muted, fontSize: 12, lineHeight: 18, marginTop: 3 },
  percent: { color: stitch.blue, fontSize: 24, fontWeight: "900" },
  progressTrack: { height: 7, borderRadius: 5, backgroundColor: stitch.surfaceHigh, marginTop: 14, overflow: "hidden" },
  progressFill: { height: "100%", backgroundColor: stitch.blue, borderRadius: 5 },
  section: { padding: 16, gap: 12 },
  sectionHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  sectionTitle: { color: stitch.text, fontSize: 18, fontWeight: "900" },
  sectionAction: { color: stitch.blue, fontSize: 13, fontWeight: "900" },
  evidenceRow: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 8 },
  evidenceTitle: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  evidenceBody: { color: stitch.outline, fontSize: 12, marginTop: 2 },
  warningCard: { padding: 16, backgroundColor: stitch.redSoft, flexDirection: "row", alignItems: "center", gap: 12, borderColor: "rgba(186,26,26,0.18)" },
  warningIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  warningTitle: { color: stitch.red, fontSize: 15, fontWeight: "900" },
  warningText: { color: stitch.text, fontSize: 12, lineHeight: 18, marginTop: 2 },
  aiCard: { borderRadius: 12, backgroundColor: stitch.surface, borderWidth: 1, borderColor: "rgba(198,198,205,0.45)", padding: 16, flexDirection: "row", alignItems: "center", gap: 12 },
  aiIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  aiTitle: { color: stitch.text, fontSize: 16, fontWeight: "900" },
  aiBody: { color: stitch.muted, fontSize: 12, lineHeight: 18, marginTop: 2 },
  aiButton: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  timeline: { flexDirection: "row", gap: 12, paddingVertical: 8 },
  timelineIcon: { width: 34, height: 34, borderRadius: 17, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  timelineTitle: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  timelineTime: { color: stitch.outline, fontSize: 11, marginTop: 1 },
  timelineBody: { color: stitch.muted, fontSize: 12, lineHeight: 18, marginTop: 4 },
});
