/**
 * GPS 백그라운드 추적 서비스 (Capacitor 네이티브 앱 전용).
 *
 * - 앱이 백그라운드에서도 위치를 수집하여 Backend /gps/ping 으로 전송
 * - 웹 브라우저에서는 동작하지 않음 (Capacitor.isNativePlatform 체크)
 * - 위조 감지: is_mocked 플래그 전달
 */
import { Capacitor } from "@capacitor/core";
import { fetchApi } from "./api";

const IS_NATIVE = Capacitor.isNativePlatform();

let bgGeo: any = null;

export async function startGpsTracking(caseId: string) {
  if (!IS_NATIVE) {
    // 웹: 포그라운드 Geolocation API 사용 (기존 방식)
    return startWebGps(caseId);
  }

  // 네이티브: 백그라운드 플러그인 (런타임에만 로드, 빌드 타임에는 무시)
  let BackgroundGeolocation: any;
  try {
    const mod = "@transistorsoft/capacitor-background-geolocation";
    BackgroundGeolocation = (await import(/* webpackIgnore: true */ mod as any)).default;
  } catch {
    // 패키지 없으면 웹 fallback
    return startWebGps(caseId);
  }

  bgGeo = BackgroundGeolocation;

  await bgGeo.ready({
    desiredAccuracy: bgGeo.DESIRED_ACCURACY_HIGH,
    distanceFilter: 10, // 10m 이동 시마다 기록
    stopOnTerminate: false,
    startOnBoot: true,
    enableHeadless: true,
    locationAuthorizationRequest: "Always",
    backgroundPermissionRationale: {
      title: "BADA 위치 추적 허용",
      message: "근무지 출퇴근 증거 수집을 위해 백그라운드 위치 권한이 필요합니다.",
      positiveAction: "허용",
      negativeAction: "거부",
    },
  });

  // 위치 수신 콜백
  bgGeo.onLocation((location: any) => {
    sendPing(caseId, location);
  });

  await bgGeo.start();
}

export async function stopGpsTracking() {
  if (bgGeo) {
    await bgGeo.stop();
  }
}

async function sendPing(caseId: string, location: any) {
  try {
    await fetchApi(`/cases/${caseId}/gps/ping`, {
      method: "POST",
      body: JSON.stringify({
        lat: location.coords.latitude,
        lng: location.coords.longitude,
        altitude_m: location.coords.altitude,
        speed_mps: location.coords.speed,
        accuracy_m: location.coords.accuracy,
        is_mocked: location.mock || false,
        provider: "app",
        source: "app",
      }),
    });
  } catch (e) {
    // 네트워크 실패 시 무시 (다음 핑에서 재시도)
    console.warn("GPS ping 전송 실패:", e);
  }
}

// 웹 포그라운드 GPS (브라우저 환경)
function startWebGps(caseId: string) {
  if (!navigator.geolocation) return;

  const intervalId = setInterval(() => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        fetchApi(`/cases/${caseId}/gps/ping`, {
          method: "POST",
          body: JSON.stringify({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            accuracy_m: pos.coords.accuracy,
            is_mocked: false,
            provider: "web_geo",
            source: "web_geo",
          }),
        }).catch(() => {});
      },
      () => {},
      { enableHighAccuracy: true }
    );
  }, 60000); // 1분 간격

  // cleanup 함수 반환
  return () => clearInterval(intervalId);
}
