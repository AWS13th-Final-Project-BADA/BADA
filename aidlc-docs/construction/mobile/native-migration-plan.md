# BADA 모바일 — 네이티브(React Native/Expo) 전환 계획서

> 작성 기준: 2026-06-24 · 브랜치 `feature/mobile-native` · 기준 분기 `develop`
> 결정: 기존 Capacitor(웹뷰 기반) 방식을 **진짜 네이티브 앱(React Native + Expo)** 으로 전환한다.
> 원칙: **develop·backend·기존 `frontend`·기존 `mobile`(Capacitor)을 건드리지 않는다.** 새 브랜치 + 새 폴더(`mobile-native/`)에서만 작업한다.

---

## 0. 왜 전환하나 (배경)

- 요구: "웹뷰가 아닌 진짜 네이티브 앱."
- 기존 `mobile/`(Capacitor)은 본질적으로 화면을 WebView로 렌더한다. 또한 문서가 둘로 갈라져 상충했다:
  - `docs/mobile-app.md` (구버전): 옛 `backend/app/static` 정적 HTML을 감쌈, `app-config.json`+`sync-web.mjs` 주소 주입.
  - `aidlc-docs/construction/mobile/mobile-setup.md` + 실제 `capacitor.config.json`: Next.js를 감싸고 `server.url=https://badasoft.com` **원격 로드**.
  - 게다가 `capacitor.config.json`(원격 로드)과 `mobile/package.json`의 `build:web`(`next export` 번들)이 **서로 모순**.
- 결론: 웹뷰가 아닌 앱을 원하면 Capacitor로는 불가 → **네이티브 재작성**. 이 경우 "Capacitor 전제 문서와의 완전 일치"는 성립할 수 없으므로, **문서를 네이티브 방향으로 갱신**하는 것을 본 계획에 포함한다.

## 1. 핵심 원칙 (불변식)

1. **격리**: 모든 네이티브 코드는 `mobile-native/`에만 둔다. develop·backend·frontend·mobile(Capacitor) 무수정.
2. **백엔드 재사용**: API는 `https://api.badasoft.com`를 그대로 호출. 백엔드 코드 변경은 최소화하며, 불가피한 변경(아래 §6 인증 콜백)은 별도 합의 후 backend 담당과 진행.
3. **steering 준수**: `product.md` 표현 정책(면책고지·금지표현)을 앱 화면·문구에 그대로 적용. `git.md` 브랜치/커밋 컨벤션 준수.
4. **자산 재사용**: 다국어 문구(`frontend/src/messages/*.json`), API 경로, 화면 흐름을 그대로 미러링한다.
5. **되돌릴 수 있음**: 막히면 `mobile-native/` 폴더와 브랜치만 폐기하면 끝. 본체 영향 0.

## 2. 기술 선택

| 항목 | 선택 | 근거 |
| --- | --- | --- |
| 프레임워크 | **React Native + Expo (SDK 51)** | 팀이 React(Next.js) 사용 → 학습곡선·자산 재사용 유리 |
| 라우팅 | **expo-router** (파일기반) | Next.js App Router와 동일 멘탈모델 |
| 보안 저장소 | **expo-secure-store** | 토큰을 localStorage 대신 OS 보안 저장소에 |
| 위치/백그라운드 | **expo-location + expo-task-manager** | "항상 허용" 백그라운드 추적, 무료(@transistorsoft 유료 의존 제거) |
| 카메라/파일 | **expo-image-picker / expo-document-picker** | 증거 업로드 |
| 인증 | **expo-web-browser (+ deep link)** | 기존 Cognito 리다이렉트 흐름 재사용 |
| 다국어 | **i18n-js + expo-localization** | 기존 ko/vi/en JSON 그대로 |
| 푸시(후순위) | expo-notifications | Phase 2 |

> ⚠️ `@transistorsoft/capacitor-background-geolocation`는 **유료(trial)** 였다. 네이티브 전환에서 **expo-location 무료 백그라운드 추적으로 대체**해 라이선스 비용 리스크를 제거한다.

## 3. 화면 목록 (web 미러링)

| # | 화면 | web 대응 | API | MVP |
| --- | --- | --- | --- | --- |
| 1 | 홈/대시보드 | `[locale]/page.tsx` | — | P0 |
| 2 | 로그인 | `lib/auth.ts` | `/auth/cognito/login`, 소셜 | P0 |
| 3 | 사건 목록 | `[locale]/cases/page.tsx` | `GET /cases` | P0 |
| 4 | 사건 상세 | (web 미구현) | `GET /cases/{id}` | P0 |
| 5 | 새 사건 | (web `/cases/new`) | `POST /cases` | P1 |
| 6 | 증거 업로드 | (messages.upload) | presigned `PUT`, `POST /evidences` | P1 |
| 7 | 분석 결과 | (messages.analysis) | `GET /cases/{id}/analysis` | P1 |
| 8 | 타임라인 | (messages.analysis.timeline) | 분석 결과 내 | P1 |
| 9 | GPS 추적 | `lib/gps.ts`, web gps page | `POST /gps/ping` | P0(차별점) |
| 10 | Evidence Pack PDF 보기 | `/cases/{id}/report.pdf` | PDF 뷰어/다운로드 | P2 |
| 11 | 커뮤니티 | (nav.community) | `/community/*` | P2 |
| 12 | AI 챗봇 | (nav.chat) | `/chat` 또는 kakao 로직 | P2 |

## 4. 단계별 로드맵 (bolt 단위)

### Bolt M1 — 뼈대 & 핵심 동작 (이번 세션 범위)
- Expo 프로젝트 구조, API 클라이언트(SecureStore 토큰), i18n(ko/vi/en), expo-router 네비게이션.
- 화면: 홈, 로그인, 사건 목록, 사건 상세(읽기), GPS 백그라운드 데모.
- 산출물: 실행 가능한 `mobile-native/` (팀이 `npm install` 후 `npx expo` 로 구동).

### Bolt M2 — 증거 파이프라인
- 새 사건 생성, 카메라/파일 업로드(presigned), 분석 실행·결과·타임라인 화면.
- **사람 게이트**: 면책고지·금지표현 톤 검수(product.md).

### Bolt M3 — 부가 기능 & 출시 준비
- 커뮤니티, 챗봇, PDF 뷰어, 푸시.
- Android 릴리스 서명 키 + `.aab` 빌드(EAS Build), Play Console 업로드 준비.
- iOS는 Mac/Xcode 확보 시 동일 흐름(`eas build -p ios`).

## 5. 디렉토리 구조

```
mobile-native/
├─ app.json                 # Expo 설정(앱명/스킴/권한/배경위치)
├─ package.json
├─ tsconfig.json / babel.config.js
├─ app/                     # expo-router 화면(파일기반)
│  ├─ _layout.tsx           # 루트 스택 + i18n/auth provider
│  ├─ index.tsx             # 홈
│  ├─ login.tsx             # 로그인(Cognito/소셜)
│  ├─ gps.tsx               # 백그라운드 GPS 데모
│  └─ cases/
│     ├─ index.tsx          # 사건 목록
│     └─ [id].tsx           # 사건 상세
├─ src/
│  ├─ lib/api.ts            # Bearer 토큰 자동주입 클라이언트
│  ├─ lib/auth.ts           # Cognito 로그인(웹브라우저+딥링크)
│  ├─ lib/gps.ts            # expo-location 백그라운드 → /gps/ping
│  ├─ theme.ts              # 색/간격 토큰
│  └─ i18n/
│     ├─ index.ts
│     └─ messages/{ko,vi,en}.json   # frontend에서 복사
└─ README.md                # 셋업/실행/빌드 안내
```

## 6. 인증(중요) — 백엔드 연계 포인트

웹은 `/auth/cognito/login` → Cognito → 백엔드 콜백 → **`#token=...` 해시로 웹에 반환**한다.
네이티브는 브라우저 세션을 열고 **앱 스킴 딥링크(`bada://auth?token=...`)** 로 토큰을 돌려받아야 한다.

- 클라이언트(`src/lib/auth.ts`)는 `expo-web-browser`로 로그인 URL을 열고 `bada://auth` 리다이렉트에서 토큰을 추출하도록 구현되어 있다.
- **백엔드 합의 필요(1건)**: 콜백이 `redirect_uri`(또는 `app=1`) 파라미터를 받으면 웹 해시 대신 **앱 스킴으로 302 리다이렉트**하도록 한 분기 추가. (현 웹 흐름은 무변경 유지)
- 합의 전까지는 데모용으로 토큰 수동 주입(개발 메뉴)도 지원한다.

## 7. 문서 정합성 작업

- `docs/mobile-app.md`, `aidlc-docs/construction/mobile/mobile-setup.md` 상단에 **"Capacitor 기준(전환 중)" 배너**를 달고 본 계획서를 가리킨다(이력 보존, 삭제 안 함).
- 향후 `.kiro/steering/tech.md`의 모바일 스택 문구는 네이티브 확정 시 팀 합의로 갱신(현재는 계획서에서만 선언).

## 8. 리스크 & 대응

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| 팀 Dart/RN 미숙 | 속도 저하 | RN 선택으로 React 자산·지식 재사용 |
| 인증 딥링크 백엔드 미지원 | 로그인 막힘 | §6 한 분기 추가(소규모) + 데모 토큰 주입 폴백 |
| 백그라운드 위치 권한(Android 14) | 추적 누락 | "항상 허용" 안내 UX + 포그라운드 서비스 알림 |
| Expo 빌드 환경 | 출시 지연 | EAS Build(클라우드 빌드)로 로컬 SDK 부담 최소화 |
| develop 충돌 | 본체 손상 | 새 브랜치+새 폴더 격리, 본체 무수정 |
| 두 코드베이스(web+app) 유지 | 중복 | 문구/타입/규칙은 공유, UI만 분리. RN 단일 프레임워크 유지 |

## 9. 완료 정의 (이번 세션)

- [ ] `feature/mobile-native` 브랜치 생성 (완료)
- [ ] `mobile-native/` 실행 가능한 Expo 스캐폴드
- [ ] 홈/로그인/사건목록/사건상세/GPS 데모 화면
- [ ] API 클라이언트·i18n·SecureStore 토큰
- [ ] 상충 문서 배너 정리 + 본 계획서
- [ ] README 셋업 안내
