# 모바일 앱 — React Native (Expo) 설계·설정

> 모바일의 **단일 설계 문서(source of truth)**. 기존 Capacitor(웹뷰) 방식에서 **진짜 네이티브 앱(React Native + Expo)** 으로 전환했다.
> 원칙: develop·backend·기존 `frontend`·기존 `mobile`(Capacitor) **무수정.** 새 브랜치 `feature/mobile-native` + 새 폴더 `mobile-native/`에서만 작업한다.
> (구버전 Capacitor 안내는 `docs/mobile-app.md` 참고 — 이력 보존용.)

---

## 0. 전환 배경

- 요구: "웹뷰가 아닌 진짜 네이티브 앱."
- 기존 `mobile/`(Capacitor)은 화면을 WebView로 렌더하며, 문서가 둘로 갈라져 상충했다(원격 로드 vs `next export` 번들).
- 결론: 웹뷰가 아닌 앱은 Capacitor로 불가 → **네이티브 재작성(React Native/Expo).** 이로 인해 "Capacitor 전제 문서와의 일치"는 성립하지 않으므로, 본 문서를 네이티브 기준으로 갱신한다.

## 1. 불변식

1. **격리**: 모든 네이티브 코드는 `mobile-native/`에만. 본체(develop·backend·frontend·mobile) 무수정.
2. **백엔드 재사용**: API는 `https://api.badasoft.com` 그대로 호출. 백엔드 변경은 최소화하며, 불가피한 3건(§6)은 담당자와 협의.
3. **steering 준수**: `product.md` 표현 정책(면책고지·금지표현)을 화면·문구에 적용. `git.md` 브랜치/커밋 컨벤션 준수.
4. **자산 재사용**: 다국어 문구(`frontend/src/messages/*.json`), API 경로, 화면 흐름을 미러링.
5. **되돌릴 수 있음**: 막히면 `mobile-native/` 폴더·브랜치만 폐기 → 본체 영향 0.

## 2. 기술 선택

| 항목 | 선택 | 근거 |
| --- | --- | --- |
| 프레임워크 | **React Native + Expo (SDK 51)** | 팀이 React 사용 → 학습곡선·자산 재사용 유리 |
| 라우팅 | **expo-router** (파일기반) | Next.js App Router와 동일 멘탈모델 |
| 보안 저장소 | **expo-secure-store** | 토큰을 OS 보안 저장소에 |
| 위치/백그라운드 | **expo-location + expo-task-manager** | 무료(유료 `@transistorsoft` 대체) |
| 카메라/파일 | **expo-image-picker / expo-document-picker** | 증거 업로드 |
| 인증 | **expo-web-browser (+ 딥링크)** | 기존 Cognito 리다이렉트 흐름 재사용 |
| 다국어 | **i18n-js + expo-localization** | 기존 ko/vi/en JSON 그대로 |

## 3. 설정 & 실행

```bash
cd mobile-native
npm install
npx expo start          # QR → 폰 Expo Go 스캔, 또는 a(안드로이드)/i(iOS)
```

백그라운드 위치 등 네이티브 모듈 실검증은 개발 빌드가 필요(Expo Go 불가):
```bash
npx expo prebuild        # ios/ android/ 생성(.gitignore 처리됨)
npx expo run:android     # 실기기/에뮬에 개발 빌드 설치
```
- API 주소: `app.json` → `expo.extra.apiBase`(기본 `https://api.badasoft.com`)
- 앱 스킴: `bada://`, package: `com.bada.app`

## 4. 구조

```
mobile-native/
├─ app.json / package.json / tsconfig.json / babel.config.js
├─ app/                     # expo-router 화면(파일기반)
│  ├─ _layout.tsx · index.tsx · login.tsx · gps.tsx
│  └─ cases/(index·[id]·new·upload·analysis) · community/(index·new·[id]) · chat.tsx
├─ src/
│  ├─ shared/(api · theme · types)            # 공유 transport·테마·primitives 타입
│  ├─ features/                               # 기능별 모듈(2026-06-24 재배치)
│  │   ├─ auth/api · evidence/(api·types) · gps/api
│  │   └─ cases/types · analysis/types · community/types · chat/types
│  ├─ lib/(api·auth·gps·evidence·types) · theme.ts   # 기존 import 호환 배럴(재export)
│  └─ i18n/(index + messages/ko·vi·en.json)   # frontend에서 복사(중앙 집중)
├─ CONTRIBUTING.md          # 충돌 없는 협업 규약(기능 모듈 경계·핫스팟·브랜치)
└─ BACKEND-INTEGRATION.md   # 백엔드 연계 3건(§6)
```

## 5. 화면 목록 & 로드맵 (현재 상태)

| 단계 | 범위 | 상태 |
| --- | --- | --- |
| **M1** | 뼈대 + 홈/로그인/사건 목록·상세/GPS 데모 + API·i18n·토큰 | ✅ 완료 |
| **M2** | 새 사건 생성 · 증거 업로드(카메라/갤러리/PDF) · 분석 결과(+report.html) | ✅ 완료 |
| **M3** | 커뮤니티(피드/작성/상세·댓글·공감) · AI 챗봇 · Evidence Pack 리포트 | ✅ 완료 |
| **검증** | 에뮬레이터 실행 성공(홈 렌더, AI 챗봇 백엔드 실연결 확인) | ✅ 2026-06-24 |
| **GPS 수정** | 사건 종속 전환 + 근무지 등록 + 포그라운드 추적(Expo Go 동작) · 챗봇 언어 `auto` | ✅ 2026-06-24 |
| **남음** | 백그라운드 GPS(개발빌드) · 디자인 마감 · 법무(동의·삭제) · 인계물·출시빌드 | ⏳ |

> 화면은 백엔드 계약(`schemas.py`·`schemas_report.py`·`schemas_community.py`·`schemas_ai_chat.py`)에 맞춰 구현. 모든 사용자 대면 문구에 면책고지 적용.

## 6. 백엔드 연계 필요 3건 (담당자 협의)

> 셋 다 "추가·게이트" 방식 — 기존 웹 동작 무영향. 상세·검증법은 `mobile-native/BACKEND-INTEGRATION.md`.

1. **인증 딥링크 (최우선)** — `auth.py` 콜백이 토큰을 웹(`#token=`)으로만 반환 → 앱이 못 받음. `redirect_uri=bada://auth`면 앱 스킴으로 302 분기 추가. (인증/Cognito 담당)
2. **챗봇 `case_id` 정합** — `schemas_ai_chat.py` `case_id: int` ↔ 사건 UUID 불일치. `str` 수용으로 변경. (GPS+Agent+OCR 담당)
3. **`report.pdf` 다운로드** — 워커가 PDF를 S3(`pdf_ko_s3_key`)에 저장하나 노출 엔드포인트 없음. `presign_get` 302 엔드포인트 1개 추가. 후순위. (백엔드/분석 담당)

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

## 9. 리스크

| 리스크 | 대응 |
| --- | --- |
| 인증 딥링크 백엔드 미지원 | §6-1 분기 추가 + 데모용 토큰 주입 폴백 |
| 백그라운드 위치 권한(Expo Go 불가) | 개발 빌드 + "항상 허용" 안내 |
| 출시 빌드 환경 | EAS Build(클라우드)로 로컬 부담 최소화 |
| 두 코드베이스(web+app) 유지 | 문구/타입/규칙 공유, UI만 분리(RN 단일 유지) |
| 팀 문서 불일치 | 팀 상태표·OWNERSHIP의 "모바일=Capacitor" 갱신 필요(팀 합의) |
