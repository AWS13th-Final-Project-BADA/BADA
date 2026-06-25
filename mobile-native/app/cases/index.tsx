import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { ApiError, fetchApi } from "@/lib/api";
import type { Case } from "@/lib/types";
import { Chip, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";

export default function CasesList() {
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await fetchApi<Case[]>("/cases");
      setCases(Array.isArray(data) ? data : []);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) router.replace("/login");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <StitchScreen active="cases">
      <TopBar title="사건 목록" />
      <View style={styles.content}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>내 사건</Text>
            <Text style={styles.subtitle}>상담 준비 상태와 업로드한 자료를 확인하세요.</Text>
          </View>
          <Pressable style={styles.iconButton} onPress={() => router.push("/cases/new")}>
            <MaterialIcons name="add" size={24} color={stitch.navy} />
          </Pressable>
        </View>

        {loading ? (
          <ActivityIndicator color={stitch.blue} style={{ marginTop: 48 }} />
        ) : cases.length > 0 ? (
          <View style={styles.list}>
            {cases.map((item) => (
              <CaseCard
                key={item.id}
                item={item}
                onPress={() => router.push({ pathname: "/cases/[id]", params: { id: item.id } })}
              />
            ))}
          </View>
        ) : (
          <View style={styles.empty}>
            <View style={styles.emptyImage}>
              <MaterialIcons name="folder-open" size={72} color={stitch.line} />
            </View>
            <Text style={styles.emptyTitle}>진행 중인 사건이 없어요</Text>
            <Text style={styles.emptyBody}>자료를 모아 상담 가능한 사건 파일을 만들어 보세요.</Text>
            <StitchButton onPress={() => router.push("/cases/new")}>새 사건 시작하기</StitchButton>
          </View>
        )}
      </View>
    </StitchScreen>
  );
}

function CaseCard({
  item,
  onPress,
}: {
  item: Case;
  onPress: () => void;
}) {
  const readiness = item.status === "completed" ? 100 : 65;
  const issueLabel = item.issue_types?.includes("deduction") ? "공제 확인" : "임금 확인";

  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.cardTop}>
        <View style={{ flex: 1 }}>
          <Text style={styles.caseTitle}>{item.workplace_name || item.employer_name || "사업장 미입력"}</Text>
          <View style={styles.tagRow}>
            <Chip label={issueLabel} tone="blue" />
            <Chip label={item.status === "completed" ? "완료" : "상담 준비"} tone={item.status === "completed" ? "green" : "blue"} />
          </View>
        </View>
        <MaterialIcons name="chevron-right" size={24} color={stitch.outline} />
      </View>

      <View style={styles.readinessRow}>
        <Text style={styles.readinessLabel}>준비도</Text>
        <Text style={styles.readinessValue}>{readiness}%</Text>
      </View>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${readiness}%` }]} />
      </View>

      <View style={styles.metaRow}>
        <Meta icon="event" text={item.work_start_date || "기간 미입력"} />
        <Meta icon="payments" text={item.agreed_hourly_wage ? `${item.agreed_hourly_wage.toLocaleString()}원` : "임금 미입력"} />
      </View>
    </Pressable>
  );
}

function Meta({ icon, text }: { icon: keyof typeof MaterialIcons.glyphMap; text: string }) {
  return (
    <View style={styles.meta}>
      <MaterialIcons name={icon} size={18} color={stitch.outline} />
      <Text style={styles.metaText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 18 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  title: { color: stitch.text, fontSize: 28, lineHeight: 36, fontWeight: "900" },
  subtitle: { marginTop: 4, color: stitch.muted, fontSize: 14, fontWeight: "700" },
  iconButton: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: stitch.surfaceLow },
  list: { gap: 16 },
  card: { backgroundColor: stitch.surface, borderRadius: 12, borderWidth: 1, borderColor: "rgba(198,198,205,0.45)", padding: 20, gap: 14 },
  cardTop: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  caseTitle: { color: stitch.text, fontSize: 20, lineHeight: 28, fontWeight: "900" },
  tagRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10 },
  readinessRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  readinessLabel: { color: stitch.outline, fontSize: 12, fontWeight: "800" },
  readinessValue: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  progressTrack: { height: 8, borderRadius: 4, backgroundColor: stitch.surfaceHigh, overflow: "hidden" },
  progressFill: { height: "100%", borderRadius: 4, backgroundColor: stitch.blue },
  metaRow: { flexDirection: "row", flexWrap: "wrap", gap: 20 },
  meta: { flexDirection: "row", alignItems: "center", gap: 6 },
  metaText: { color: stitch.outline, fontSize: 12, fontWeight: "700" },
  empty: { alignItems: "center", paddingTop: 80, gap: 16 },
  emptyImage: { width: 180, height: 130, borderRadius: 16, alignItems: "center", justifyContent: "center", backgroundColor: stitch.surfaceLow },
  emptyTitle: { color: stitch.text, fontSize: 20, fontWeight: "900", textAlign: "center" },
  emptyBody: { color: stitch.muted, fontSize: 14, textAlign: "center", lineHeight: 21 },
});
