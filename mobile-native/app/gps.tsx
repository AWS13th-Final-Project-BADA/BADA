import { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Alert,
  ScrollView,
} from "react-native";
import {
  requestPermissions,
  startTracking,
  stopTracking,
  isTracking,
  getCurrent,
} from "@/lib/gps";
import { colors, spacing, radius } from "@/theme";

export default function GpsScreen() {
  const [tracking, setTracking] = useState(false);
  const [coords, setCoords] = useState<string>("—");

  async function refresh() {
    setTracking(await isTracking());
  }
  useEffect(() => {
    refresh();
  }, []);

  async function onStart() {
    const ok = await requestPermissions();
    if (!ok) {
      Alert.alert(
        "위치 권한 필요",
        "백그라운드 추적을 위해 위치 권한을 '항상 허용'으로 설정해 주세요."
      );
      return;
    }
    await startTracking();
    await refresh();
  }

  async function onStop() {
    await stopTracking();
    await refresh();
  }

  async function onCheck() {
    const loc = await getCurrent();
    if (loc) {
      setCoords(
        `${loc.coords.latitude.toFixed(5)}, ${loc.coords.longitude.toFixed(5)}` +
          (((loc as any).mocked) ? "  ⚠️ mock 감지" : "")
      );
    } else {
      setCoords("위치를 가져오지 못했습니다.");
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.h1}>GPS 근무 증거</Text>
      <Text style={styles.desc}>
        재직 중 근무지 출입을 백그라운드에서 자동 기록합니다. 수집된 위치는
        서버로 전송되어 분쟁 시 근무 사실의 교차검증 증거로 활용됩니다.
      </Text>

      <View style={[styles.statusBox, tracking && styles.statusOn]}>
        <Text style={styles.statusText}>
          {tracking ? "● 추적 중" : "○ 중지됨"}
        </Text>
      </View>

      {tracking ? (
        <Pressable style={[styles.btn, styles.stop]} onPress={onStop}>
          <Text style={styles.btnText}>추적 중지</Text>
        </Pressable>
      ) : (
        <Pressable style={styles.btn} onPress={onStart}>
          <Text style={styles.btnText}>백그라운드 추적 시작</Text>
        </Pressable>
      )}

      <Pressable style={styles.secondary} onPress={onCheck}>
        <Text style={styles.secondaryText}>현재 위치 확인</Text>
      </Pressable>
      <Text style={styles.coords}>{coords}</Text>

      <Text style={styles.note}>
        ⚠️ 위치 위조(mock)가 감지된 핑은 증거에서 배제됩니다(무결성 보장).
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.md },
  h1: { fontSize: 22, fontWeight: "800", color: colors.text },
  desc: { color: colors.textMuted, lineHeight: 20 },
  statusBox: {
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.badge,
    alignItems: "center",
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
  secondary: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: "center",
  },
  secondaryText: { color: colors.text, fontWeight: "600" },
  coords: { textAlign: "center", color: colors.textMuted, fontSize: 13 },
  note: { fontSize: 12, color: colors.textMuted, marginTop: spacing.md },
});
