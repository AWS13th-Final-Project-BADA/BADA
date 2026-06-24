import * as Location from "expo-location";
import { fetchApi } from "./api";

export interface Workplace {
  id?: string;
  center_lat: number;
  center_lng: number;
  radius_m: number;
}

export interface PingResult {
  stored?: boolean;
  ok?: boolean;
  inside?: boolean;
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
    const last = await Location.getLastKnownPositionAsync();
    if (last) return last;
  } catch {
    // Try active lookup below.
  }

  try {
    return await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
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
        // The next location update will retry.
      }
    }
  );
}
