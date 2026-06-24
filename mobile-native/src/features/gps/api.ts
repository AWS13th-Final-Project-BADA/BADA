/**
 * GPS — 사건 종속(case-scoped) + 포그라운드 추적.
 * 백엔드 계약(backend/app/routers/gps.py):
 *   POST /cases/{id}/gps/workplace  {center_lat, center_lng, radius_m(10~500)}
 *   GET  /cases/{id}/gps/workplace
 *   POST /cases/{id}/gps/ping       {ts, lat, lng, is_mocked, source}
 *
 * 포그라운드(앱이 열린 동안) watchPositionAsync 사용 → Expo Go에서 동작.
 * 백그라운드(앱 꺼져도 추적)는 개발 빌드 필요 → 추후(mobile-setup.md §7).
 */
import * as Location from "expo-location";
import { fetchApi } from "@/lib/api";

export interface Workplace {
  id: string;
  center_lat: number;
  center_lng: number;
  radius_m: number;
}

export interface PingResult {
  stored: boolean;
  status: string | null; // IN_WORKPLACE | OUTSIDE | UNKNOWN | null(mock)
  distance_m: number | null;
  warning?: string;
}

export async function requestForeground(): Promise<boolean> {
  const fg = await Location.requestForegroundPermissionsAsync();
  return fg.status === "granted";
}

export async function getCurrent(): Promise<Location.LocationObject | null> {
  // 1) 마지막으로 알려진 위치 — 에뮬레이터/실내에서 즉시 반환되는 경우가 많음
  try {
    const last = await Location.getLastKnownPositionAsync();
    if (last) return last;
  } catch {
    /* fall through */
  }
  // 2) 새 위치 측정 시도
  try {
    return await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
  } catch {
    return null;
  }
}

/** 근무지(지오펜스) 등록. */
export async function registerWorkplace(
  caseId: string,
  lat: number,
  lng: number,
  radiusM: number
): Promise<Workplace> {
  return fetchApi<Workplace>(`/cases/${caseId}/gps/workplace`, {
    method: "POST",
    body: JSON.stringify({
      center_lat: lat,
      center_lng: lng,
      radius_m: radiusM,
    }),
  });
}

/** 등록된 근무지 조회(없으면 null). */
export async function getWorkplace(caseId: string): Promise<Workplace | null> {
  try {
    return await fetchApi<Workplace>(`/cases/${caseId}/gps/workplace`);
  } catch {
    return null; // 404 = 미등록
  }
}

/** 위치 핑 1건 전송 → IN/OUT 즉시 판정 결과 반환. */
export async function sendPing(
  caseId: string,
  loc: Location.LocationObject
): Promise<PingResult> {
  return fetchApi<PingResult>(`/cases/${caseId}/gps/ping`, {
    method: "POST",
    body: JSON.stringify({
      ts: new Date(loc.timestamp).toISOString(),
      lat: loc.coords.latitude,
      lng: loc.coords.longitude,
      is_mocked: (loc as any).mocked ?? false, // 위치 위조 감지 → 증거 배제
      source: "app",
    }),
  });
}

/**
 * 포그라운드 추적 시작 — 앱이 열려 있는 동안 위치 변화마다 핑 전송.
 * 반환된 subscription.remove() 로 중지.
 */
export async function startForegroundWatch(
  caseId: string,
  onPing: (loc: Location.LocationObject, result: PingResult) => void
): Promise<Location.LocationSubscription> {
  return Location.watchPositionAsync(
    {
      accuracy: Location.Accuracy.Balanced,
      distanceInterval: 10, // 10m 이동마다
      timeInterval: 15000, // 또는 15초마다
    },
    async (loc) => {
      try {
        const result = await sendPing(caseId, loc);
        onPing(loc, result);
      } catch {
        // 오프라인/일시 실패는 다음 갱신에서 재시도
      }
    }
  );
}
