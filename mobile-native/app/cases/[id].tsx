import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { fetchApi } from "@/lib/api";
import type { Case, EvidenceItem } from "@/lib/types";
import { Card, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

export default function CaseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { locale } = useLocale();
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
    return (
      <StitchScreen active="cases">
        <TopBar title="BADA" back />
        <ActivityIndicator color={stitch.blue} style={{ marginTop: 80 }} />
      </StitchScreen>
    );
  }

  const title = data?.workplace_name || data?.employer_name || t("cases.detail");
  const completedEvidence = evidences.filter((item) => item.ocr_status === "done" || item.ocr_status === "completed").length;
  const readiness = Math.min(100, 35 + evidences.length * 15 + completedEvidence * 10);

  return (
    <StitchScreen active="cases">
      <TopBar title={t("cases.detail")} back />
      <View style={styles.content}>
        <View style={styles.caseHead}>
          <Text style={styles.caseId}>Case #{String(id || "").slice(0, 8)}</Text>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.status}>
            {t("cases.status")}: <Text style={styles.statusStrong}>{data?.status === "completed" ? t("home.stats.ready") : t("home.stats.preparing")}</Text>
          </Text>
        </View>

        <View style={styles.actionRow}>
          <Action icon="upload-file" label={t("cases.upload")} onPress={() => router.push({ pathname: "/cases/upload", params: { caseId: id } })} />
          <Action icon="analytics" label={t("cases.uploadHistory")} onPress={() => router.push({ pathname: "/cases/analysis", params: { caseId: id } })} />
        </View>

        <Card style={styles.readiness}>
          <View style={styles.readinessTop}>
            <View style={styles.readinessIcon}><MaterialIcons name="verified-user" size={24} color={stitch.blue} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.readinessLabel}>{t("cases.readiness")}</Text>
              <Text style={styles.readinessBody}>{t("home.dashboardSubtitle")}</Text>
            </View>
            <Text style={styles.percent}>{readiness}%</Text>
          </View>
          <View style={styles.progressTrack}><View style={[styles.progressFill, { width: `${readiness}%` }]} /></View>
        </Card>

        <Section title={t("cases.evidenceCount")} action={t("cases.actions.addMore")} onAction={() => router.push({ pathname: "/cases/upload", params: { caseId: id } })}>
          {evidences.length ? (
            evidences.slice(0, 5).map((item) => (
              <EvidenceRow
                key={item.id}
                ok={item.ocr_status === "done" || item.ocr_status === "completed"}
                title={item.file_name}
                body={item.category ? t("upload.categories." + item.category) : t("upload.category")}
              />
            ))
          ) : (
            <EvidenceRow warning title={t("upload.emptyTitle")} body={t("upload.emptyBody")} />
          )}
        </Section>

        <Pressable style={styles.aiCard} onPress={() => router.push({ pathname: "/chat", params: { caseId: id } })}>
          <View style={styles.aiIcon}><MaterialIcons name="smart-toy" size={26} color={stitch.blue} /></View>
          <View style={{ flex: 1 }}>
            <Text style={styles.aiTitle}>{t("chat.title")}</Text>
            <Text style={styles.aiBody}>{t("chat.subtitle")}</Text>
          </View>
          <Text style={styles.aiButton}>{t("common.confirm")}</Text>
        </Pressable>

        <Section title={t("home.nextTitle")}>
          <Timeline icon="description" title={t("cases.actions.upload")} time="1" body={t("cases.actions.uploadBody")} />
          <Timeline icon="payments" title={t("cases.actions.addMore")} time="2" body={t("cases.actions.addMoreBody")} />
          <Timeline icon="chat" title={t("cases.actions.chat")} time="3" body={t("cases.actions.chatBody")} />
        </Section>
      </View>
    </StitchScreen>
  );
}

function Action({ icon, label, onPress }: { icon: keyof typeof MaterialIcons.glyphMap; label: string; onPress: () => void }) {
  return (
    <Pressable style={styles.action} onPress={onPress}>
      <MaterialIcons name={icon} size={22} color="#fff" />
      <Text style={styles.actionText}>{label}</Text>
    </Pressable>
  );
}

function Section({ title, action, onAction, children }: { title: string; action?: string; onAction?: () => void; children: React.ReactNode }) {
  return (
    <Card style={styles.section}>
      <View style={styles.sectionHead}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {action ? <Pressable onPress={onAction}><Text style={styles.sectionAction}>{action}</Text></Pressable> : null}
      </View>
      {children}
    </Card>
  );
}

function EvidenceRow({ ok, warning, title, body }: { ok?: boolean; warning?: boolean; title: string; body: string }) {
  return (
    <View style={styles.evidenceRow}>
      <MaterialIcons name={ok ? "check-circle" : warning ? "warning" : "radio-button-unchecked"} size={24} color={ok ? stitch.green : warning ? stitch.amber : stitch.outline} />
      <View style={{ flex: 1 }}>
        <Text style={styles.evidenceTitle} numberOfLines={1}>{title}</Text>
        <Text style={styles.evidenceBody}>{body}</Text>
      </View>
      <MaterialIcons name="more-vert" size={22} color={stitch.outline} />
    </View>
  );
}

function Timeline({ icon, title, time, body }: { icon: keyof typeof MaterialIcons.glyphMap; title: string; time: string; body: string }) {
  return (
    <View style={styles.timeline}>
      <View style={styles.timelineIcon}><MaterialIcons name={icon} size={20} color={stitch.blue} /></View>
      <View style={{ flex: 1 }}>
        <Text style={styles.timelineTitle}>{title}</Text>
        <Text style={styles.timelineTime}>{time}</Text>
        <Text style={styles.timelineBody}>{body}</Text>
      </View>
    </View>
  );
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
