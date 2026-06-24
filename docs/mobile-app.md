# BADA 모바일 앱 (Capacitor · Android)

> ⚠️ **[전환 중 — 2026-06-24]** 이 문서는 **Capacitor(웹뷰 기반)** 방식 기준이며, 옛 `backend/app/static` 프론트를 전제로 한 **구버전**이다.
> 현재 모바일은 **진짜 네이티브 앱(React Native + Expo)** 으로 전환됐다 → **`aidlc-docs/construction/mobile/mobile-setup.md`**(설계·설정) 및 **`mobile-native/`**(코드) 참조.
> 이력 보존을 위해 본문은 그대로 둔다. 신규 작업은 `mobile-native/`에서 진행한다.

웹 프론트(`backend/app/static`)를 **그대로 네이티브 앱으로 감싸는** 방식. 코드 한 벌로 웹·앱 공용.

## 무엇이 되나
- 스토어에 올라가는 **실제 Android 앱**(`.apk`/`.aab`)
- 카메라 촬영(웹 input 그대로 동작), 위치(플러그인), 오프라인 셸
- API는 설정한 백엔드 주소로 통신 (앱은 localhost 못 봄 → PC IP 또는 배포 URL)

---

## 사전 준비 (1회)
- **Node.js 18+**
- **Android Studio** (Android SDK 포함) — Mac 불필요
- 폰과 PC가 **같은 Wi-Fi**

## 1) 백엔드를 폰이 접속 가능하게 띄우기
```powershell
cd "C:\Users\dy981\OneDrive\바탕 화면\BADA\backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
`--host 0.0.0.0` 이 핵심 (기본 localhost면 폰에서 접속 불가). PC IP 확인: `ipconfig` → IPv4 주소(예: `192.168.0.10`).

## 2) 백엔드 주소 설정
`mobile/app-config.json` 의 `apiBase` 를 본인 PC IP로:
```json
{ "apiBase": "http://192.168.0.10:8000" }
```
(나중에 AWS 등에 배포하면 그 `https://...` 주소로 교체)

## 3) 설치 + Android 프로젝트 생성
```powershell
cd "C:\Users\dy981\OneDrive\바탕 화면\BADA\mobile"
npm install
npm run build            # backend/app/static → www (주소 주입)
npx cap add android             # 안드로이드 네이티브 프로젝트 생성 (최초 1회)
npx capacitor-assets generate --android   # 앱 아이콘·스플래시 생성 (mobile/assets 기반)
npx cap sync android
```

## 4) 실행
```powershell
npx cap open android     # Android Studio 열림 → 기기/에뮬 선택 → Run ▶
```
또는 기기 연결 후: `npx cap run android`

## 5) 코드 바꾼 뒤 반영
프론트(`backend/app/static`) 수정 후:
```powershell
cd mobile
npm run build && npx cap sync android
```

---

## 스토어 출시 (나중)
1. 백엔드를 실제 서버(AWS 등 HTTPS)에 배포 → `app-config.json` 의 `apiBase` 를 그 URL로.
2. Android Studio에서 서명 키(keystore) 생성 → `.aab` 빌드 → Google Play Console($25, 1회)에 업로드.
3. iOS는 Mac+Xcode + Apple 개발자 계정($99/년) 필요. `npx cap add ios` 후 동일 흐름.

## 구조
```
mobile/
  package.json          Capacitor 의존성·스크립트
  capacitor.config.json 앱 ID·이름·webDir·cleartext(개발용 http 허용)
  app-config.json       ← 백엔드 주소만 여기서 바꿈
  sync-web.mjs          웹자산 → www 복사 + 주소 주입
  www/                  (생성물, git 제외)
  android/              (cap add 로 생성, git 제외)
```

## 주의
- 개발 중 http 접속 위해 `capacitor.config.json` 에 `cleartext: true` 설정됨. 배포 땐 HTTPS 백엔드 권장.
- 카메라는 웹 `<input capture>` 로 동작. 네이티브 카메라/백그라운드 GPS가 필요하면 `@capacitor/camera`·`@capacitor-community/background-geolocation` 추가 후 `gps.js`에서 `Capacitor.Plugins.Geolocation` 사용(확장 지점).
- 프론트 코드는 웹과 100% 공용 — `window.apiUrl()` 이 웹에선 같은 출처(""), 앱에선 설정 주소로 자동 분기.
