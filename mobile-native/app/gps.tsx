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
  getLogs,
  getSummary,
  type PingResult,
  type Workplace,
  type GpsLogEntry,
  type GpsDaySummary,
} from "@/lib/gps";
import { Card, RemoteImage, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { stitchImages } from "@/lib/stitchAssets";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

const RADIUS_PRESETS = [50, 80, 100, 200, 500];

export default function GpsScreen() {
  const params = useLocalSearchParams<{ caseId?: string }>();
  const router = useRouter();
  const { locale } = useLocale();
  const [caseId, setCaseId] = useState<string>(params.caseId || "demo-case-1");
  const [cases, setCases] = useState<Case[]>([]);
  const [workplace, setWorkplace] = useState<Workplace | null>(null);
  const [radiusM, setRadiusM] = useState(80);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [tracking, setTracking] = useState(false);
  const [lastStatus, setLastStatus] = useState(t("gps.empty"));
  const subRef = useRef<Location.LocationSubscription | null>(null);
  const [logs, setLogs] = useState<GpsLogEntry[]>([]);
  const [summary, setSummary] = useState<GpsDaySummary[]>([]);

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
      // GPS 로그 + 일별 요약 로드
      try { const ld = await getLogs(selected); setLogs(ld.logs || []); } catch {}
      try { const sd = await getSummary(selected); setSummary(sd.summary || []); } catch {}
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
      Alert.alert(t("gps.permissionError"), t("gps.permissionError"));
      return;
    }
    setBusy(true);
    try {
      const loc = await getCurrent();
      if (!loc) {
        Alert.alert(t("gps.saveError"), t("gps.saveError"));
        return;
      }
      const wp = await registerWorkplace(caseId, loc.coords.latitude, loc.coords.longitude, radiusM);
      setWorkplace(wp);
      setLastStatus(t("gps.saveWorkplace"));
    } catch (e: any) {
      Alert.alert(t("gps.saveError"), String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function pingOnce() {
    const ok = await requestForeground();
    if (!ok) {
      Alert.alert(t("gps.permissionError"), t("gps.permissionError"));
      return null;
    }
    const loc = await getCurrent();
    if (!loc) {
      Alert.alert(t("gps.saveError"), t("gps.saveError"));
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
      setLastStatus(t("gps.inactive"));
      return;
    }

    try {
      await pingOnce();
      subRef.current = await startForegroundWatch(caseId, (_loc, result) => {
        setLastStatus(formatStatus(result));
      });
      setTracking(true);
    } catch (e: any) {
      Alert.alert(t("gps.saveError"), String(e?.message ?? e));
    }
  }

  if (loading) {
    return (
      <StitchScreen scroll={false} active="cases">
        <TopBar title={t("gps.title")} back />
        <View style={styles.center}>
          <ActivityIndicator color={stitch.blue} />
        </View>
      </StitchScreen>
    );
  }

  return (
    <StitchScreen scroll={false} active="cases">
      <TopBar title={t("gps.title")} back right="notifications-none" />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Card style={styles.hero}>
          <View style={styles.heroTop}>
            <View>
              <Text style={styles.heroTitle}>{t("gps.title")}</Text>
              <View style={styles.statusLine}>
                <View style={[styles.statusDot, tracking && styles.statusDotOn]} />
                <Text style={[styles.statusText, tracking && styles.statusTextOn]}>
                  {tracking ? t("gps.active") : t("gps.inactive")}
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
              <Text style={styles.statLabel}>{t("gps.logs")}</Text>
              <Text style={styles.statValue}>{tracking ? t("gps.active") : t("gps.empty")}</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statLabel}>{t("gps.summary")}</Text>
              <Text style={styles.statValue}>±{workplace?.radius_m ?? radiusM}m</Text>
            </View>
          </View>
        </Card>

        <View style={styles.sectionTop}>
          <Text style={styles.sectionTitle}>{t("gps.saveWorkplace")}</Text>
          <Text style={styles.sectionAction}>{t("gps.checkArea")}</Text>
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
              {workplace ? `${workplace.center_lat.toFixed(4)}, ${workplace.center_lng.toFixed(4)}` : t("gps.workplaceHint")}
            </Text>
          </View>
        </View>

        <Card style={styles.radiusCard}>
          <Text style={styles.radiusTitle}>{t("gps.saveWorkplace")}</Text>
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
            <Text style={styles.registerText}>{busy ? t("common.loading") : workplace ? t("gps.saveWorkplace") : t("gps.saveWorkplace")}</Text>
          </StitchButton>
        </Card>

        <Card style={styles.privacy}>
          <MaterialIcons name="verified-user" size={34} color={stitch.blueSoft} />
          <View style={{ flex: 1 }}>
            <Text style={styles.privacyTitle}>{t("gps.subtitle")}</Text>
            <Text style={styles.privacyBody}>{t("gps.workplaceHint")}</Text>
          </View>
        </Card>

        <View style={styles.sectionTop}>
          <Text style={styles.sectionTitle}>{t("gps.logs")}</Text>
          <Pressable onPress={pingOnce}>
            <Text style={styles.sectionAction}>{t("common.refresh")}</Text>
          </Pressable>
        </View>
        <View style={styles.logs}>
          <Log icon="check-circle" title={t("gps.inside")} detail={lastStatus} badge={tracking ? t("gps.active") : t("gps.inactive")} color={stitch.green} />
          <Log icon="sensors" title={t("gps.summary")} detail={t("gps.subtitle")} badge={t("common.confirm")} color={stitch.blue} />
          <Log icon="location-on" title={t("cases.detail")} detail={cases.find((item) => item.id === caseId)?.workplace_name || ""} badge={t("common.confirm")} color={stitch.muted} />
        </View>

        {/* 일별 출근 요약 */}
        {summary.length > 0 && (
          <View style={{ marginTop: 18, gap: 8 }}>
            <Text style={{ fontSize: 16, fontWeight: "700", color: stitch.text }}>{t("gps.dailySummary")}</Text>
            {summary.slice(0, 7).map((day) => (
              <Card key={day.work_date} style={{ padding: 12, gap: 2 }}>
                <Text style={{ fontWeight: "700", color: stitch.text }}>{day.work_date}</Text>
                <Text style={{ color: stitch.muted, fontSize: 13 }}>
                  {t("gps.dayStat", { in: day.in_count, out: day.out_count, hours: day.estimated_hours })}
                </Text>
                {day.first_in && (
                  <Text style={{ color: stitch.outline, fontSize: 12 }}>
                    {t("gps.dayInOut", { first: day.first_in.split(" ")[1] || day.first_in, last: day.last_out?.split(" ")[1] || "—" })}
                  </Text>
                )}
              </Card>
            ))}
          </View>
        )}

        {/* 최근 GPS 로그 */}
        {logs.length > 0 && (
          <View style={{ marginTop: 18, gap: 6 }}>
            <Text style={{ fontSize: 16, fontWeight: "700", color: stitch.text }}>{t("gps.recentLogs", { count: logs.length })}</Text>
            {logs.slice(-10).reverse().map((log) => (
              <View key={log.id} style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 3 }}>
                <Text style={{ fontWeight: "700", fontSize: 12, width: 30, color: log.status === "IN_WORKPLACE" ? stitch.green : stitch.muted }}>
                  {log.status === "IN_WORKPLACE" ? "IN" : log.status === "OUTSIDE" ? "OUT" : "—"}
                </Text>
                <Text style={{ color: stitch.outline, fontSize: 12 }}>{new Date(log.ts).toLocaleTimeString("ko-KR")}</Text>
              </View>
            ))}
          </View>
        )}
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
  if (!result) return t("gps.empty");
  if (result.status === "IN_WORKPLACE" || result.inside) return `${t("gps.inside")} (${result.distance_m ?? "?"}m)`;
  if (result.status === "OUTSIDE") return `${t("gps.outside")} (${result.distance_m ?? "?"}m)`;
  if (result.status === null) return t("gps.permissionError");
  return result.status || t("gps.active");
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
