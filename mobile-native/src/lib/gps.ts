/**
 * 백그라운드 GPS 추적 — expo-location + expo-task-manager.
 * (@transistorsoft 유료 플러그인 대체 — 무료/네이티브)
 *
 * 동작: "항상 허용" 권한 획득 → 위치 갱신마다 Backend `POST /gps/ping` 전송.
 * BADA 차별점: 재직 중 실시간 근무 증거 수집(steering product.md §2 하이브리드).
 *
 * is_mocked: 위치 위조(mock) 감지 플래그를 백엔드로 전달(증거 신빙성, security.md §6).
 */
import * as Location from "expo-location";
import * as TaskManager from "expo-task-manager";
import { fetchApi } from "./api";

export const GPS_TASK = "bada-background-location";

async function sendPing(loc: Location.LocationObject, caseId?: string) {
  const body = {
    case_id: caseId ?? null,
    ts: new Date(loc.timestamp).toISOString(),
    lat: loc.coords.latitude,
    lng: loc.coords.longitude,
    accuracy: loc.coords.accuracy ?? null,
    // expo는 mocked 플래그를 Android에서 제공(없으면 false)
    is_mocked: (loc as any).mocked ?? false,
  };
  try {
    await fetchApi("/gps/ping", { method: "POST", body: JSON.stringify(body) });
  } catch {
    // 오프라인/실패는 조용히 무시(다음 핑에서 재시도). 큐잉은 M2에서 보강.
  }
}

// 백그라운드 태스크 정의(모듈 로드 시 1회 등록)
TaskManager.defineTask(GPS_TASK, async ({ data, error }) => {
  if (error) return;
  const { locations } = (data as any) ?? {};
  if (!locations?.length) return;
  for (const loc of locations as Location.LocationObject[]) {
    await sendPing(loc);
  }
});

export async function requestPermissions(): Promise<boolean> {
  const fg = await Location.requestForegroundPermissionsAsync();
  if (fg.status !== "granted") return false;
  const bg = await Location.requestBackgroundPermissionsAsync();
  return bg.status === "granted";
}

export async function startTracking(): Promise<void> {
  const has = await Location.hasStartedLocationUpdatesAsync(GPS_TASK).catch(
    () => false
  );
  if (has) return;
  await Location.startLocationUpdatesAsync(GPS_TASK, {
    accuracy: Location.Accuracy.Balanced,
    distanceInterval: 10, // 10m 이동마다(mobile-setup.md 규칙과 동일)
    deferredUpdatesInterval: 30000,
    showsBackgroundLocationIndicator: true,
    foregroundService: {
      notificationTitle: "BADA 위치 수집 중",
      notificationBody: "근무 증거를 위해 위치를 기록하고 있습니다.",
      notificationColor: "#2563eb",
    },
  });
}

export async function stopTracking(): Promise<void> {
  const has = await Location.hasStartedLocationUpdatesAsync(GPS_TASK).catch(
    () => false
  );
  if (has) await Location.stopLocationUpdatesAsync(GPS_TASK);
}

export async function isTracking(): Promise<boolean> {
  return Location.hasStartedLocationUpdatesAsync(GPS_TASK).catch(() => false);
}

export async function getCurrent(): Promise<Location.LocationObject | null> {
  try {
    return await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
  } catch {
    return null;
  }
}
