import { useEffect, useState, useCallback, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";
import * as Location from "expo-location";
import { useLocalSearchParams, useRouter } from "expo-router";
import { fetchApi, ApiError } from "@/lib/api";
import type { Case } from "@/lib/types";
import {
  requestForeground,
  getCurrent,
  getWorkplace,
  registerWorkplace,
  startForegroundWatch,
  type Workplace,
  type PingResult,
} from "@/lib/gps";
import { colors, spacing, radius } from "@/theme";

const RADIUS_PRESETS = [50, 100, 200, 300, 500];

export default function GpsScreen() {
  const params = useLocalSearchParams<{ caseId?: string }>();
  const router = useRouter();

  const [caseId, setCaseId] = useState<string | null>(params.caseId ?? null);
  const [cases, setCases] = useState<Case[]>([]);
  const [workplace, setWorkplace] = useState<Workplace | null>(null);
  const [radiusM, setRadiusM] = useState(100);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [tracking, setTracking] = useState(false);
  const [lastStatus, setLastStatus] = useState<string>("—");
  const subRef = useRef<Location.LocationSubscription | null>(null);

  // 사건 미지정 시 목록 로드 / 지정 시 근무지 로드
  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (!caseId) {
        const list = await fetchApi<Case[]>("/cases");
        setCases(Array.isArray(list) ? list : []);
      } else {
        setWorkplace(await getWorkplace(caseId));
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        Alert.alert(
          "로그인 필요",
          "GPS는 로그인 후 사용할 수 있어요. 먼저 로그인(또는 개발용 토큰 주입)을 해주세요.",
          [{ text: "로그인으로", onPress: () => router.push("/login") }]
        );
      }
    } finally {
      setLoading(false);
    }
  }, [caseId, router]);

  useEffect(() => {
    load();
  }, [load]);

  // 화면 떠날 때 추적 정리
  useEffect(() => {
    return () => {
      subRef.current?.remove();
    };
  }, []);

  async function onRegisterWorkplace() {
    if (!caseId) return;
    const ok = await requestForeground();
    if (!ok) {
      Alert.alert("위치 권한 필요", "근무지 등록을 위해 위치 권한을 허용해 주세요.");
      return;
    }
    setBusy(true);
    try {
      const loc = await getCurrent();
      if (!loc) {
        Alert.alert("오류", "현재 위치를 가져오지 못했습니다.");
        return;
      }
      const wp = await registerWorkplace(
        caseId,
        loc.coords.latitude,
        loc.coords.longitude,
        radiusM
      );
      setWorkplace(wp);
    } catch (e: any) {
      Alert.alert("등록 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function onStart() {
    if (!caseId) return;
    const ok = await requestForeground();
    if (!ok) {
      Alert.alert("위치 권한 필요", "위치 권한을 허용해 주세요.");
      return;
    }
    subRef.current = await startForegroundWatch(caseId, (_loc, r: PingResult) => {
      setLastStatus(formatStatus(r));
    });
    setTracking(true);
  }

  function onStop() {
    subRef.current?.remove();
    subRef.current = null;
    setTracking(false);
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  // 1) 사건 선택 화면
  if (!caseId) {
    return (
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.h1}>GPS 근무 증거</Text>
        <Text style={styles.desc}>
          어느 사건의 근무 위치를 기록할지 먼저 선택하세요.
        </Text>
        {cases.length === 0 ? (
          <Text style={styles.muted}>
            사건이 없습니다. 먼저 사건을 만들어 주세요.
          </Text>
        ) : (
          cases.map((c) => (
            <Pressable
              key={c.id}
              style={styles.caseRow}
              onPress={() => setCaseId(c.id)}
            >
              <Text style={styles.caseName}>
                {c.workplace_name || "(무제 사건)"}
              </Text>
              <Text style={styles.muted}>{c.status}</Text>
            </Pressable>
          ))
        )}
      </ScrollView>
    );
  }

  // 2) 근무지 미등록 → 등록 화면
  if (!workplace) {
    return (
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.h1}>근무지 등록</Text>
        <Text style={styles.desc}>
          현재 위치를 이 사건의 근무지로 등록합니다. 등록한 원(반경) 안에 있으면
          "출근 중"으로 판정돼요.
        </Text>

        <Text style={styles.label}>인정 반경</Text>
        <View style={styles.chips}>
          {RADIUS_PRESETS.map((r) => {
            const on = r === radiusM;
            return (
              <Pressable
                key={r}
                style={[styles.chip, on && styles.chipOn]}
                onPress={() => setRadiusM(r)}
              >
                <Text style={[styles.chipText, on && styles.chipTextOn]}>
                  {r}m
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Pressable style={styles.btn} onPress={onRegisterWorkplace} disabled={busy}>
          {busy ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.btnText}>현재 위치를 근무지로 등록</Text>
          )}
        </Pressable>
      </ScrollView>
    );
  }

  // 3) 추적 화면
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.h1}>GPS 근무 증거</Text>
      <Text style={styles.desc}>
        근무지: {workplace.center_lat.toFixed(5)},{" "}
        {workplace.center_lng.toFixed(5)} · 반경 {workplace.radius_m}m
      </Text>

      <View style={[styles.statusBox, tracking && styles.statusOn]}>
        <Text style={styles.statusText}>
          {tracking ? "● 추적 중" : "○ 중지됨"}
        </Text>
        <Text style={styles.muted}>최근 판정: {lastStatus}</Text>
      </View>

      {tracking ? (
        <Pressable style={[styles.btn, styles.stop]} onPress={onStop}>
          <Text style={styles.btnText}>추적 중지</Text>
        </Pressable>
      ) : (
        <Pressable style={styles.btn} onPress={onStart}>
          <Text style={styles.btnText}>추적 시작 (앱 켜진 동안)</Text>
        </Pressable>
      )}

      <Text style={styles.note}>
        ⚠️ 위치 위조(mock)가 감지된 핑은 증거에서 자동 배제됩니다. 앱을 꺼도
        추적되는 백그라운드 모드는 개발 빌드에서 지원됩니다.
      </Text>
    </ScrollView>
  );
}

function formatStatus(r: PingResult): string {
  if (r.status === "IN_WORKPLACE")
    return `출근 중 (${r.distance_m ?? "?"}m)`;
  if (r.status === "OUTSIDE") return `근무지 밖 (${r.distance_m ?? "?"}m)`;
  if (r.status === null) return "⚠️ 위치 위조 감지(배제됨)";
  return r.status ?? "—";
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.md },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  h1: { fontSize: 22, fontWeight: "800", color: colors.text },
  desc: { color: colors.textMuted, lineHeight: 20 },
  label: { fontSize: 13, color: colors.textMuted, fontWeight: "600" },
  muted: { color: colors.textMuted, fontSize: 13 },
  caseRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  caseName: { fontWeight: "600", color: colors.text, fontSize: 15 },
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
  statusBox: {
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.badge,
    gap: 4,
  },
  statusOn: { backgroundColor: "#dcfce7" },
  statusText: { fontWeight: "700", color: colors.text },
  btn: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
  },
  stop: { backgroundColor: colors.danger },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  note: { fontSize: 12, color: colors.textMuted, lineHeight: 18, marginTop: spacing.md },
});
