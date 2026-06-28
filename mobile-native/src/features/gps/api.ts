import * as Location from "expo-location";
import { fetchApi } from "@/lib/api";

export interface Workplace {
  id?: string;
  center_lat: number;
  center_lng: number;
  radius_m: number;
}

export interface PingResult {
  ok?: boolean;
  stored: boolean;
  inside?: boolean | null;
  status: string | null;
  distance_m: number | null;
  warning?: string;
}

export async function requestForeground(): Promise<boolean> {
  const fg = await Location.requestForegroundPermissionsAsync();
  return fg.status === "granted";
}

export async function getCurrent(): Promise<Location.LocationObject | null> {
  try {
    const cur = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.High,
    });
    if (cur) return cur;
  } catch {
    // Fallback to cached location below.
  }

  try {
    return await Location.getLastKnownPositionAsync();
  } catch {
    return null;
  }
}

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

export async function getWorkplace(caseId: string): Promise<Workplace | null> {
  try {
    return await fetchApi<Workplace>(`/cases/${caseId}/gps/workplace`);
  } catch {
    return null;
  }
}

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
      is_mocked: (loc as any).mocked ?? false,
      source: "app",
    }),
  });
}

export async function startForegroundWatch(
  caseId: string,
  onPing: (loc: Location.LocationObject, result: PingResult) => void
): Promise<Location.LocationSubscription> {
  return Location.watchPositionAsync(
    {
      accuracy: Location.Accuracy.Balanced,
      distanceInterval: 100,
      timeInterval: 300000,
    },
    async (loc) => {
      try {
        const result = await sendPing(caseId, loc);
        onPing(loc, result);
      } catch {
        // The next watch update will retry.
      }
    }
  );
}

// ── GPS 로그 조회 + 일별 요약 ────────────────────────────────────────────

export interface GpsLogEntry {
  id: string;
  ts: string;
  lat: number;
  lng: number;
  status: string | null;
  source: string;
}

export interface GpsDaySummary {
  work_date: string;
  in_count: number;
  out_count: number;
  first_in: string | null;
  last_out: string | null;
  estimated_hours: number;
  hours_method: string;
  delayed_pings?: number;
  delayed_warning?: string;
}

export async function getLogs(caseId: string): Promise<{ count: number; logs: GpsLogEntry[] }> {
  return fetchApi(`/cases/${caseId}/gps/logs`);
}

export async function getSummary(
  caseId: string
): Promise<{ total_days: number; summary: GpsDaySummary[]; integrity: { sha256: string; generated_at: string } }> {
  return fetchApi(`/cases/${caseId}/gps/summary`);
}
