import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Switch, Text, View } from "react-native";
import * as Location from "expo-location";
import { useLocalSearchParams, useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import type { Case } from "@/lib/types";
import { fetchApi, ApiError } from "@/lib/api";
import {
  getCurrent,
  getWorkplace,
  registerWorkplace,
  requestForeground,
  sendPing,
  startForegroundWatch,
  type PingResult,
  type Workplace,
} from "@/lib/gps";
import { Card, RemoteImage, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { stitchImages } from "@/lib/stitchAssets";

const RADIUS_PRESETS = [50, 80, 100, 200, 500];

export default function GpsScreen() {
  const params = useLocalSearchParams<{ caseId?: string }>();
  const router = useRouter();
  const [caseId, setCaseId] = useState<string>(params.caseId || "demo-case-1");
  const [cases, setCases] = useState<Case[]>([]);
  const [workplace, setWorkplace] = useState<Workplace | null>(null);
  const [radiusM, setRadiusM] = useState(80);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [tracking, setTracking] = useState(false);
  const [lastStatus, setLastStatus] = useState("아직 기록 없음");
  const subRef = useRef<Location.LocationSubscription | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await fetchApi<Case[]>("/cases");
      setCases(Array.isArray(list) ? list : []);
      const selected = params.caseId || list?.[0]?.id || caseId;
      setCaseId(selected);
      const wp = await getWorkplace(selected);
      setWorkplace(wp);
      if (wp?.radius_m) setRadiusM(wp.radius_m);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [caseId, params.caseId, router]);

  useEffect(() => {
    void load();
    return () => {
      subRef.current?.remove();
    };
  }, [load]);

  async function onRegisterWorkplace() {
    const ok = await requestForeground();
    if (!ok) {
      Alert.alert("위치 권한 필요", "근무지 등록을 위해 위치 권한을 허용해 주세요.");
      return;
    }
    setBusy(true);
    try {
      const loc = await getCurrent();
      if (!loc) {
        Alert.alert("위치 확인 실패", "현재 위치를 가져오지 못했어요.");
        return;
      }
      const wp = await registerWorkplace(caseId, loc.coords.latitude, loc.coords.longitude, radiusM);
      setWorkplace(wp);
      setLastStatus("근무지 기준점이 등록됐어요.");
    } catch (e: any) {
      Alert.alert("등록 실패", String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function pingOnce() {
    const ok = await requestForeground();
    if (!ok) {
      Alert.alert("위치 권한 필요", "위치 권한을 허용해 주세요.");
      return null;
    }
    const loc = await getCurrent();
    if (!loc) {
      Alert.alert("위치 확인 실패", "현재 위치를 가져오지 못했어요.");
      return null;
    }
    const result = await sendPing(caseId, loc);
    setLastStatus(formatStatus(result));
    return result;
  }

  async function toggleTracking(next: boolean) {
    if (!next) {
      subRef.current?.remove();
      subRef.current = null;
      setTracking(false);
      setLastStatus("기록이 일시 중지됐어요.");
      return;
    }

    try {
      await pingOnce();
      subRef.current = await startForegroundWatch(caseId, (_loc, result) => {
        setLastStatus(formatStatus(result));
      });
      setTracking(true);
    } catch (e: any) {
      Alert.alert("기록 시작 실패", String(e?.message ?? e));
    }
  }

  if (loading) {
    return (
      <StitchScreen scroll={false} active="cases">
        <TopBar title="GPS 기록" back />
        <View style={styles.center}>
          <ActivityIndicator color={stitch.blue} />
        </View>
      </StitchScreen>
    );
  }

  return (
    <StitchScreen scroll={false} active="cases">
      <TopBar title="GPS 기록" back right="notifications-none" />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Card style={styles.hero}>
          <View style={styles.heroTop}>
            <View>
              <Text style={styles.heroTitle}>근무지 GPS 기록</Text>
              <View style={styles.statusLine}>
                <View style={[styles.statusDot, tracking && styles.statusDotOn]} />
                <Text style={[styles.statusText, tracking && styles.statusTextOn]}>
                  {tracking ? "기록 중" : "기록 대기"}
                </Text>
              </View>
            </View>
            <Switch
              value={tracking}
              onValueChange={toggleTracking}
              trackColor={{ false: stitch.surfaceHigh, true: stitch.blueStrong }}
              thumbColor="#fff"
            />
          </View>

          <View style={styles.statsGrid}>
            <View style={styles.statBox}>
              <Text style={styles.statLabel}>최근 기록</Text>
              <Text style={styles.statValue}>{tracking ? "방금 전" : "없음"}</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statLabel}>기록 반경</Text>
              <Text style={styles.statValue}>±{workplace?.radius_m ?? radiusM}m</Text>
            </View>
          </View>
        </Card>

        <View style={styles.sectionTop}>
          <Text style={styles.sectionTitle}>근무지 반경</Text>
          <Text style={styles.sectionAction}>구역 확인</Text>
        </View>
        <View style={styles.mapCard}>
          <RemoteImage uri={stitchImages.map} style={styles.mapImage} />
          <View style={styles.mapOverlay}>
            <View style={styles.radiusCircle}>
              <View style={styles.locationDot} />
            </View>
          </View>
          <View style={styles.legend}>
            <Text style={styles.legendText}>
              {workplace ? `${workplace.center_lat.toFixed(4)}, ${workplace.center_lng.toFixed(4)}` : "근무지 기준점 미등록"}
            </Text>
          </View>
        </View>

        <Card style={styles.radiusCard}>
          <Text style={styles.radiusTitle}>반경 설정</Text>
          <View style={styles.radiusChips}>
            {RADIUS_PRESETS.map((r) => (
              <Pressable
                key={r}
                style={[styles.radiusChip, r === radiusM && styles.radiusChipOn]}
                onPress={() => setRadiusM(r)}
              >
                <Text style={[styles.radiusChipText, r === radiusM && styles.radiusChipTextOn]}>{r}m</Text>
              </Pressable>
            ))}
          </View>
          <StitchButton tone="secondary" onPress={onRegisterWorkplace} disabled={busy}>
            <Text style={styles.registerText}>{busy ? "등록 중..." : workplace ? "현재 위치로 근무지 다시 등록" : "현재 위치를 근무지로 등록"}</Text>
          </StitchButton>
        </Card>

        <Card style={styles.privacy}>
          <MaterialIcons name="verified-user" size={34} color={stitch.blueSoft} />
          <View style={{ flex: 1 }}>
            <Text style={styles.privacyTitle}>개인정보 보호 기록</Text>
            <Text style={styles.privacyBody}>
              지정한 근무지 반경 안에서만 출근 증거로 쓸 수 있는 위치 기록을 남깁니다. 기록은 상담 준비 자료로만 사용됩니다.
            </Text>
          </View>
        </Card>

        <View style={styles.sectionTop}>
          <Text style={styles.sectionTitle}>최근 증거 로그</Text>
          <Pressable onPress={pingOnce}>
            <Text style={styles.sectionAction}>새로고침</Text>
          </Pressable>
        </View>
        <View style={styles.logs}>
          <Log icon="check-circle" title="출근 위치 확인" detail={lastStatus} badge={tracking ? "자동" : "대기"} color={stitch.green} />
          <Log icon="sensors" title="주기 기록" detail="5분 또는 100m 이동 시 확인" badge="설정" color={stitch.blue} />
          <Log icon="location-on" title="현재 케이스" detail={cases.find((item) => item.id === caseId)?.workplace_name || "바다식품"} badge="연결됨" color={stitch.muted} />
        </View>
      </ScrollView>
    </StitchScreen>
  );
}

function Log({
  icon,
  title,
  detail,
  badge,
  color,
}: {
  icon: keyof typeof MaterialIcons.glyphMap;
  title: string;
  detail: string;
  badge: string;
  color: string;
}) {
  return (
    <Card style={styles.logCard}>
      <View style={[styles.logIcon, { backgroundColor: `${color}1A` }]}>
        <MaterialIcons name={icon} size={22} color={color} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.logTitle}>{title}</Text>
        <Text style={styles.logDetail}>{detail}</Text>
      </View>
      <Text style={styles.logBadge}>{badge}</Text>
    </Card>
  );
}

function formatStatus(result: PingResult | null): string {
  if (!result) return "아직 기록 없음";
  if (result.status === "IN_WORKPLACE" || result.inside) return `근무지 안 (${result.distance_m ?? "?"}m)`;
  if (result.status === "OUTSIDE") return `근무지 밖 (${result.distance_m ?? "?"}m)`;
  if (result.status === null) return "위치 위조 또는 상태 확인 필요";
  return result.status || "기록됨";
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 18, paddingBottom: 112 },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  hero: { padding: 20, gap: 16 },
  heroTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  heroTitle: { color: stitch.text, fontSize: 22, lineHeight: 30, fontWeight: "900" },
  statusLine: { marginTop: 6, flexDirection: "row", alignItems: "center", gap: 7 },
  statusDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: stitch.outline },
  statusDotOn: { backgroundColor: stitch.green },
  statusText: { color: stitch.outline, fontSize: 12, fontWeight: "900" },
  statusTextOn: { color: stitch.green },
  statsGrid: { flexDirection: "row", gap: 12 },
  statBox: { flex: 1, borderRadius: 8, backgroundColor: stitch.surfaceLow, padding: 14 },
  statLabel: { color: stitch.outline, fontSize: 11, fontWeight: "900" },
  statValue: { marginTop: 4, color: stitch.text, fontSize: 18, fontWeight: "900" },
  sectionTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  sectionTitle: { color: stitch.text, fontSize: 20, fontWeight: "900" },
  sectionAction: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  mapCard: { height: 230, borderRadius: 12, overflow: "hidden", borderWidth: 1, borderColor: "rgba(198,198,205,0.45)", backgroundColor: stitch.surfaceHigh },
  mapImage: { height: "100%", borderRadius: 0 },
  mapOverlay: { ...StyleSheet.absoluteFillObject, alignItems: "center", justifyContent: "center" },
  radiusCircle: { width: 160, height: 160, borderRadius: 80, borderWidth: 2, borderColor: "rgba(0,81,213,0.45)", backgroundColor: "rgba(0,81,213,0.1)", alignItems: "center", justifyContent: "center" },
  locationDot: { width: 16, height: 16, borderRadius: 8, backgroundColor: stitch.blue, shadowColor: stitch.blue, shadowOpacity: 0.6, shadowRadius: 12, shadowOffset: { width: 0, height: 0 }, elevation: 5 },
  legend: { position: "absolute", left: 12, bottom: 12, borderRadius: 8, backgroundColor: "rgba(255,255,255,0.82)", paddingHorizontal: 10, paddingVertical: 7, borderWidth: 1, borderColor: "rgba(255,255,255,0.6)" },
  legendText: { color: stitch.text, fontSize: 11, fontWeight: "900" },
  radiusCard: { padding: 16, gap: 14 },
  radiusTitle: { color: stitch.text, fontSize: 16, fontWeight: "900" },
  radiusChips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  radiusChip: { borderRadius: 999, backgroundColor: stitch.surfaceLow, paddingHorizontal: 14, paddingVertical: 8 },
  radiusChipOn: { backgroundColor: stitch.navy },
  radiusChipText: { color: stitch.muted, fontSize: 12, fontWeight: "900" },
  radiusChipTextOn: { color: "#fff" },
  registerText: { color: stitch.text, fontSize: 15, fontWeight: "900" },
  privacy: { padding: 18, flexDirection: "row", gap: 14, backgroundColor: "#131b2e" },
  privacyTitle: { color: "#fff", fontSize: 14, fontWeight: "900" },
  privacyBody: { marginTop: 6, color: "#bec6e0", fontSize: 13, lineHeight: 20, fontWeight: "600" },
  logs: { gap: 10 },
  logCard: { padding: 14, flexDirection: "row", alignItems: "center", gap: 12 },
  logIcon: { width: 42, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center" },
  logTitle: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  logDetail: { marginTop: 2, color: stitch.outline, fontSize: 12, fontWeight: "700" },
  logBadge: { color: stitch.outline, backgroundColor: stitch.surfaceLow, borderRadius: 5, overflow: "hidden", paddingHorizontal: 8, paddingVertical: 4, fontSize: 11, fontWeight: "900" },
});
