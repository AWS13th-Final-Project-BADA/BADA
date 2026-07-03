# 모바일 앱 - React Native (Expo) 설계 및 설정

> 모바일 앱의 단일 설계 문서(source of truth).
> 기존 Capacitor(WebView) 방식은 사용하지 않으며, 현재 앱 화면과 로직의 기준 소스는 `mobile-native/`이다.
> 최종 갱신: 2026-07-03

---

## 0. 전환 배경

- GPS, 촬영, 파일 선택, 딥링크 로그인을 실제 모바일 경험으로 제공하기 위해 React Native(Expo)로 전환했다.
- `frontend/`를 WebView로 띄우지 않고 React Native 컴포넌트가 네이티브 UI를 렌더링한다.
- 웹의 문구와 API 계약은 재사용하되 화면과 앱 상태 관리는 모바일 전용으로 구현한다.

## 1. 구현 원칙

1. 앱 화면과 앱 전용 로직은 `mobile-native/`에 둔다.
2. 기본 API는 `https://api.badasoft.com`이며 Android 에뮬레이터 로컬 테스트에서만 `http://10.0.2.2:8000`을 임시 사용한다.
3. 자체 JWT는 SecureStore에 저장하고 Bearer 헤더로 전송한다.
4. 한국어, 영어, 베트남어, 일본어, 크메르어 번역 키를 동일하게 유지한다.
5. 법률 판단을 단정하지 않고 자료 정리와 상담 준비 중심으로 안내한다.
6. PR 전 `app.json`의 운영 API와 공식 EAS owner/projectId를 확인한다. 임시 계정·토큰·로컬 설정은 커밋하지 않는다.

## 2. 기술 선택

| 항목 | 선택 | 적용 방식 |
| --- | --- | --- |
| 프레임워크 | React Native + Expo SDK 51 | 네이티브 UI와 Expo 빌드 |
| 라우팅 | expo-router | `app/` 파일 기반 화면 이동 |
| 토큰 저장 | expo-secure-store | 자체 JWT를 OS 보안 저장소에 저장 |
| OAuth | expo-web-browser + Linking | Google/Kakao/Naver OAuth 후 `bada://auth` 복귀 |
| 위치 | expo-location + expo-task-manager | GPS 기록과 백그라운드 확장 |
| 파일 | expo-image-picker / expo-document-picker | 이미지와 PDF 증거 선택 |
| 다국어 | i18n-js + expo-localization | ko/en/vi/ja/km 메시지 |
| API | 공통 fetch 클라이언트 | Bearer 토큰, 오류 정규화, 운영/로컬 API 전환 |

## 3. 설정 및 실행

```bash
cd mobile-native
npm install
npx expo start -c
```

Android 에뮬레이터가 실행 중이면 Metro 화면에서 `a`를 누른다.

```bash
adb devices
npm exec tsc -- --noEmit
npm run check:i18n
```

백그라운드 위치 등 Expo Go에서 지원하지 않는 기능은 개발 빌드나 APK에서 검증한다.

```bash
npx expo run:android
# 또는
npx eas build -p android --profile preview
```

운영 설정은 `app.json`의 `expo.extra.apiBase`, 앱 스킴 `bada://`, Android package `com.bada.app`을 기준으로 한다.

## 4. 구조

```text
mobile-native/
├─ app/
│  ├─ _layout.tsx
│  ├─ index.tsx / login.tsx / settings.tsx / notifications.tsx
│  ├─ cases/                         # 사건 생성, 목록, 상세, 업로드, 분석
│  ├─ community/                     # 목록, 작성, 상세, 댓글
│  ├─ chat.tsx                       # AI 챗봇
│  └─ gps.tsx
├─ src/
│  ├─ components/                    # 공통 TopBar, BottomNav, UI
│  ├─ features/
│  │  ├─ auth/                       # OAuth, JWT 저장, /auth/me
│  │  ├─ cases/ / evidence/ / analysis/
│  │  ├─ chat/                       # 챗봇 API 타입
│  │  ├─ community/                  # CRUD, 번역, 반응, 신고, 안전검사
│  │  └─ gps/
│  ├─ shared/                        # API client, theme, 공통 타입
│  └─ i18n/messages/                 # ko/en/vi/ja/km
├─ assets/
├─ app.json / eas.json
└─ BACKEND-INTEGRATION.md
```

## 5. 현재 구현 범위

| 기능 | 구현 내용 | 상태 |
| --- | --- | --- |
| 앱 시작 | BADA 스플래시, 로그인 상태 복원, 홈 진입 | 완료 |
| 인증 | Google/Kakao/Naver OAuth, 딥링크 복귀, JWT SecureStore 저장, `/auth/me` 확인 | 완료 |
| 사건·증거 | 사건 생성/목록/상세, 카메라·갤러리·PDF 업로드, 분석 상태 확인 | 완료 |
| 분석 | 분석 결과, 타임라인, Evidence Pack/report 연결 | 완료 |
| AI 챗봇 | UUID `case_id`, 자동 언어 감지, RAG 출처, next actions, Guardrails 표시 | 완료 |
| 커뮤니티 | 검색·정렬·내 글, CRUD, 좋아요·저장·신고, 제목·본문·댓글 번역, 안전검사 | 완료 |
| 다국어 | ko/en/vi/ja/km 화면 문구와 챗봇 언어 전달 | 완료 |
| GPS | 사건 선택, 근무지 등록, 포그라운드 핑 | 완료 |
| 검증 | TypeScript, i18n, Expo Android export, preview APK QA | 반복 수행 |

## 6. 백엔드 연동 계약

### 6.1 소셜 OAuth 및 자체 JWT

1. 앱이 `/auth/{provider}/login?redirect_uri=bada://auth`를 연다.
2. 백엔드는 OAuth state에 허용된 복귀 주소를 저장한다.
3. callback에서 provider 사용자를 내부 `users`와 연결하고 자체 JWT를 발급한다.
4. `bada://auth?token=...`으로 복귀하면 앱이 SecureStore에 저장한다.
5. 앱은 `GET /auth/me`로 인증을 확인한 뒤 보호 API에 Bearer 토큰을 보낸다.

현재 Cognito Hosted UI는 사용하지 않는다. 로그아웃은 앱 토큰 삭제가 중심이며 서버 측 refresh/revocation은 후속 보안 과제다.

### 6.2 사건·업로드·분석

- 사건 식별자는 UUID 문자열을 그대로 사용한다.
- 업로드는 백엔드 계약에 따라 multipart 또는 presigned S3 흐름을 사용한다.
- MIME과 카테고리를 전달하고 업로드 후 분석 상태와 결과를 갱신한다.
- 사건, 증거, 분석 결과와 report는 사용자 소유권 검사를 거친다.

### 6.3 AI 챗봇

- `POST /chat/messages`에 메시지, UUID `case_id`, `language: auto`를 전달한다.
- `answer`, `next_actions`, `sources`, `ai_provider`, `risk_level`, `used_rag`, `fallback_used`를 화면에 반영한다.
- 출처 칩을 누르면 기관, 문서명, 섹션, 관련 발췌문을 표시한다.
- 법률 판단 위험 질문은 다국어 Guardrails와 상담 준비 행동으로 안내한다.

### 6.4 커뮤니티

- 게시글과 댓글은 작성자만 수정·삭제할 수 있다.
- 번역은 제목과 본문을 함께 처리하고 구버전 캐시에 제목이 없으면 재번역한다.
- 개인정보와 법률 판단 요청은 작성 전 안전검사 대상이며 단순 욕설은 일괄 차단하지 않는다.

## 7. GPS — 사건 종속 + 포그라운드 (구현 완료)

- **완료(2026-06-24)**: `src/lib/gps.ts`·`app/gps.tsx`를 사건 종속 구조로 수정.
  - 흐름: **사건 선택 → 근무지 등록(`POST /cases/{id}/gps/workplace`, 반경 50~500m) → 해당 사건으로 핑 전송(`POST /cases/{id}/gps/ping`) → IN/OUT 즉시 판정.**
  - 핑 바디 = `{ts, lat, lng, is_mocked, source:"app"}` (백엔드 `Ping` 모델 일치). `is_mocked` 핑은 서버에서 증거 배제.
  - 추적은 **포그라운드**(`watchPositionAsync`) → **Expo Go에서 동작.**
- **남음**: 앱을 꺼도 추적되는 **백그라운드 모드**는 개발 빌드 필요(`expo run:android`; Expo Go는 foreground-service 권한 미포함).
- 테스트 전제: GPS 엔드포인트가 인증을 요구 → 로그인(또는 개발용 토큰 주입) 후 사건이 있어야 핑 동작.

## 8. 법무 필수 (출시 전, `docs/BADA Privacy Legal Requirements.md`)

- 가입·위치·국외이전 **동의 화면**(위치정보법: 위치는 별도 동의 필수).
- **회원 탈퇴·사건 삭제** 버튼 → RDS + **S3 원본까지 삭제**.

## 9. 테스트 및 운영 리스크

```bash
cd backend
python -m pytest -q

cd ../mobile-native
npm exec tsc -- --noEmit
npm run check:i18n
npx expo export --platform android
```

사용자 E2E는 로그인 → `/auth/me` → 사건 생성 → 업로드 → 분석 → 챗봇 RAG/Guardrails → 커뮤니티 CRUD/번역 → 로그아웃 순서로 확인한다. 상세 절차는 `docs/mobile/e2e-test.md`를 따른다.

| 리스크 | 대응 |
| --- | --- |
| OAuth provider 세션으로 계정 자동 선택 | 계정 선택 옵션과 다른 계정 로그인 QA |
| 자체 JWT 폐기/갱신 미구현 | 짧은 만료 시간, refresh/revocation 후속 설계 |
| Expo Go와 APK 동작 차이 | PR 전 Expo 검사, merge 후 APK 실기기 QA |
| 임시 EAS 설정 커밋 | 빌드 후 `git checkout -- app.json`, `git status` 확인 |
| RAG/Bedrock/AWS 의존성 | 응답 metadata와 로그로 provider/fallback 확인 |
| 번역 캐시 구버전 데이터 | 제목 누락 시 재번역, 언어별 실제 게시글 QA |
| 백그라운드 GPS 권한 | 개발 빌드와 실제 Android 권한 시나리오 검증 |
