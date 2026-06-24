# BADA 네이티브 모바일 앱 (React Native + Expo)

웹뷰가 아닌 **진짜 네이티브 앱**. 백엔드(`https://api.badasoft.com`)를 그대로 호출하며, develop·backend·기존 `frontend`·기존 `mobile`(Capacitor)과 **완전히 분리**되어 있다.

> 전환 배경·로드맵·리스크: `../aidlc-docs/construction/mobile/mobile-setup.md`

## 사전 준비 (1회)
- Node.js 18+
- (실기기/에뮬 빌드 시) Android Studio. iOS는 Mac + Xcode.
- 빠른 확인은 휴대폰에 **Expo Go** 앱 설치로 충분.

## 설치 & 실행
```bash
cd mobile-native
npm install
npx expo start          # QR 코드를 Expo Go로 스캔하거나, a(안드로이드)/i(iOS)
```

백그라운드 위치 등 네이티브 모듈을 실제로 검증하려면 개발 빌드가 필요하다:
```bash
npx expo prebuild        # ios/ android/ 네이티브 프로젝트 생성(.gitignore 처리됨)
npx expo run:android     # 실기기/에뮬에 개발 빌드 설치
```

## 구조
```
app/                 expo-router 화면(파일기반, Next.js App Router와 동일 멘탈모델)
  _layout.tsx        루트 스택 + i18n 초기화
  index.tsx          홈
  login.tsx          로그인(Cognito/소셜 + 개발용 토큰 주입)
  cases/index.tsx    사건 목록 (GET /cases)
  cases/[id].tsx     사건 상세 (GET /cases/{id})
  gps.tsx            백그라운드 GPS 데모 (POST /gps/ping)
src/
  lib/api.ts         Bearer 토큰 자동주입(SecureStore 보관)
  lib/auth.ts        Cognito 로그인(웹브라우저+딥링크)
  lib/gps.ts         expo-location 백그라운드 추적
  i18n/              ko/vi/en (frontend messages 재사용)
  theme.ts           색/간격 토큰
```

## 설정
- API 주소: `app.json` → `expo.extra.apiBase` (기본 `https://api.badasoft.com`)
- 앱 스킴: `bada://` (인증 딥링크 리다이렉트)

## 로그인에 관해(중요)
현재 백엔드 Cognito 콜백은 웹용으로 `#token=` 해시를 반환한다. 네이티브가 토큰을
받으려면 콜백이 `redirect_uri=bada://auth`를 받을 때 앱 스킴으로 302 리다이렉트하는
분기가 필요하다(계획서 §6, 백엔드 소규모 변경 1건). 그 전까지는 로그인 화면 하단의
**개발용 토큰 주입**으로 동작을 확인할 수 있다.

## 출시 준비(M3)
```bash
npm install -g eas-cli
eas build -p android --profile preview   # .apk / .aab 클라우드 빌드
```
Google Play Console 등록($25, 1회). iOS는 Apple 개발자 계정($99/년).

## 주의
- 백그라운드 위치는 Android에서 "항상 허용" 권한 + 포그라운드 서비스 알림이 필요하다.
- `@transistorsoft`(유료) 대신 **expo-location(무료)** 사용 — 라이선스 비용 없음.
