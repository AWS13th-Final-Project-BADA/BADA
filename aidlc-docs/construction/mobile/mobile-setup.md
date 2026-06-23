# 모바일 앱 (Capacitor) 설정

> ⚠️ **[전환 중 — 2026-06-24]** 이 문서는 **Capacitor(웹뷰 기반 · Next.js 원격 로드)** 방식 기준이다.
> "웹뷰가 아닌 진짜 네이티브 앱" 요구에 따라 모바일은 **React Native + Expo**로 전환 중이다.
> 최신 방향·로드맵은 **`native-migration-plan.md`**, 코드는 **`mobile-native/`** 를 참조한다.
> (참고: 본 문서 방식은 `capacitor.config.json`의 원격 로드와 `package.json`의 `next export` 번들이 서로 상충했다.)

## 구조

```
mobile/
├── capacitor.config.json   # 앱 설정 (서버 URL, 플러그인)
├── package.json            # Capacitor + 백그라운드 GPS 플러그인
├── www/                    # Next.js 빌드 산출물 (sync 시 생성)
└── android/                # Android 프로젝트 (cap add android 후 생성)
```

## 초기 설정

```bash
cd mobile
npm install
npx cap add android
```

## 빌드 및 실행

```bash
# Next.js 빌드 → Capacitor 동기화 → Android Studio 열기
npm run android

# 에뮬레이터에서 바로 실행
npm run android:run
```

## GPS 백그라운드 추적

- 플러그인: `@transistorsoft/capacitor-background-geolocation`
- 동작: 앱이 백그라운드에서도 10m 이동마다 위치 수집 → Backend `/gps/ping` 전송
- 권한: "항상 허용" 위치 권한 필요 (Android: ACCESS_BACKGROUND_LOCATION)
- 위조 감지: `location.mock` 플래그를 `is_mocked`로 전달

## 프로덕션 배포 시

```json
// capacitor.config.json
{
  "server": {
    "url": "https://badasoft.com"
  }
}
```

## 로컬 개발 시

```json
// capacitor.config.json
{
  "server": {
    "url": "http://10.0.2.2:3000"
  }
}
```
(10.0.2.2 = 안드로이드 에뮬레이터에서 호스트 PC를 가리키는 IP)
