# BADA 모바일 E2E 테스트 가이드

> 최종 갱신: 2026-07-01
> 대상: `mobile-native/` React Native(Expo) 앱과 `backend/` FastAPI API

## 1. 목적과 범위

이 문서는 모바일 사용자가 로그인한 뒤 사건을 만들고, 증거를 업로드하고, 분석 결과·AI 챗봇·커뮤니티를 사용하는 핵심 흐름을 검증한다.

검증 범위는 다음과 같다.

- Google·Kakao·Naver 소셜 OAuth와 앱 딥링크 복귀
- 자체 JWT의 SecureStore 저장 및 Bearer 헤더 주입
- `GET /auth/me` 기반 로그인 상태 확인
- 사건 생성·목록·상세 조회
- 증거 업로드와 사건 분석 흐름
- 사건 UUID 기반 AI 챗봇, RAG 출처, 다국어 Guardrails
- 커뮤니티 CRUD, 반응, 신고, 안전검사, 제목·본문·댓글 번역
- 한국어·영어·베트남어·일본어·크메르어 UI 리소스
- TypeScript, i18n 인코딩, Expo Android 번들 검증

## 2. 실행 환경

### 운영 API를 사용하는 앱

`mobile-native/app.json`의 기본 API는 다음과 같다.

```json
{
  "expo": {
    "extra": {
      "apiBase": "https://api.badasoft.com"
    }
  }
}
```

운영 API 검증에는 로컬 FastAPI 서버나 SSM 포트포워딩이 필요하지 않다.

### 로컬 API를 사용하는 Android 에뮬레이터

Android 에뮬레이터에서 PC의 FastAPI 서버를 호출할 때는 `127.0.0.1` 대신 `http://10.0.2.2:8000`을 사용한다. 이 변경은 로컬 테스트 전용이며 커밋 전에 운영 URL로 복구해야 한다.

## 3. 사용자 관점 E2E 시나리오

### 3.1 소셜 OAuth 로그인

1. 로그인 화면에서 Google, Kakao 또는 Naver를 선택한다.
2. 앱이 `GET /auth/{provider}/login?redirect_uri=<app-link>`를 호출한다.
3. 백엔드는 안전한 복귀 주소만 OAuth state에 보존한다.
4. provider 인증 후 백엔드가 자체 JWT를 발급한다.
5. `bada://auth?token=...` 또는 Expo 딥링크로 앱에 복귀한다.
6. 앱은 JWT를 SecureStore에 저장한다.
7. 앱 진입 시 `GET /auth/me`로 실제 인증 상태를 확인한다.

기대 결과:

- 앱으로 정상 복귀한다.
- 사용자 이름·이메일·provider가 표시된다.
- 이후 인증 API에 `Authorization: Bearer <token>`이 자동 첨부된다.

> 현재 인증은 Cognito Hosted UI가 아니라 백엔드 직접 소셜 OAuth + 자체 JWT 방식이다.

### 3.2 로그아웃

1. 설정 화면에서 로그아웃한다.
2. 앱의 SecureStore 토큰이 제거된다.
3. 보호된 화면 재진입 시 로그인 화면으로 이동한다.

현재 `POST /auth/logout`은 성공 응답만 반환하며 서버 측 토큰 폐기 목록은 운영하지 않는다. 따라서 로그아웃의 실제 효력은 클라이언트 토큰 삭제와 JWT 만료에 기반한다.

### 3.3 사건 생성·조회

1. 새 사건을 만든다.
2. 사건 제목, 사업장, 근무기간 등 기본 정보를 입력한다.
3. 사건 목록에서 새 사건을 확인한다.
4. 사건 상세 화면으로 이동한다.

기대 결과:

- 생성된 UUID 사건 ID가 목록과 상세 화면에서 동일하다.
- 로그인 사용자는 자신의 사건만 조회·수정할 수 있다.

### 3.4 증거 업로드·분석

1. 사건 상세에서 업로드 화면으로 이동한다.
2. 근로계약서, 급여명세서, 입금내역, 대화 캡처 등의 카테고리를 선택한다.
3. 카메라·갤러리·문서 선택기로 파일을 고른다.
4. 앱이 `POST /cases/{case_id}/evidences/upload` multipart API를 호출한다.
5. 업로드된 증거를 확인하고 분석을 실행한다.

기대 결과:

- Bearer 토큰과 사건 UUID가 함께 전달된다.
- 업로드 성공 후 증거 목록에 파일이 표시된다.
- 분석 화면에서 상태와 결과를 다시 조회할 수 있다.
- 배포 환경의 presigned S3 업로드 경로를 사용하는 경우 MIME type이 서명 요청과 PUT 요청에서 일치한다.

### 3.5 AI 챗봇·RAG·Guardrails

1. 사건 상세 또는 하단 탭에서 AI 챗봇으로 이동한다.
2. 사건을 선택한 뒤 질문을 전송한다.
3. 앱은 UUID `case_id`, `message`, `language: "auto"`를 `POST /chat/messages`로 보낸다.
4. 답변, 다음 행동, 면책문구와 RAG 출처를 확인한다.
5. 출처 칩을 눌러 기관, 문서명, 섹션, 관련 발췌문을 확인한다.

대표 질문:

```text
이 패키지에서 중요한 내용이 뭐예요?
상담할 때 무엇부터 말하면 좋을까요?
사장이 돈을 떼어갔는데 이거 불법이죠?
What should I prepare before visiting the labor office?
Tôi cần chuẩn bị gì trước khi đến Bộ Lao động?
```

기대 결과:

- 사건 선택 시 `used_case_context=true`가 반환된다.
- 공식 문서가 검색되면 `used_rag=true`이고 `sources`가 표시된다.
- 법률 판단 요구는 `risk_level=blocked` 또는 안전한 표현으로 전환된다.
- 출력 금지 표현이 감지되면 `fallback_used=true`로 안전 답변을 반환한다.
- 답변·다음 행동·면책문구는 감지된 사용자 언어와 일치한다.

### 3.6 커뮤니티

1. 게시글 목록에서 인기·최신·내 글 탭과 카테고리 필터를 확인한다.
2. 검색어로 비슷한 상황을 찾는다.
3. 게시글과 댓글을 작성·수정·삭제한다.
4. 좋아요·저장·신고를 실행한다.
5. 다른 언어의 게시글에서 번역 보기를 누른다.
6. 게시 전 안전검사를 실행한다.

기대 결과:

- 작성자 본인만 글과 댓글을 수정·삭제할 수 있다.
- 번역 결과에 게시글 제목과 본문이 함께 포함되고 댓글도 번역된다.
- 개인정보 또는 법률 판단 요구는 차단·수정 안내가 반환된다.
- 단순 욕설이나 불만만으로 일괄 차단하지 않는다.
- 반응 상태와 카운트가 새로고침 후에도 서버 값과 일치한다.

## 4. 자동 검증 명령

### 백엔드

```bash
cd backend
source .venv/Scripts/activate
python -m pytest -q
```

### 모바일 TypeScript

```bash
cd mobile-native
npm exec tsc -- --noEmit
```

### 다국어 인코딩·키 정합성

```bash
cd mobile-native
npm run check:i18n
```

### Expo Android 번들 Smoke Test

```bash
cd mobile-native
npm exec expo -- export --platform android --no-bytecode --output-dir .expo-export-check
```

### 충돌 마커와 whitespace

```bash
git diff --check
git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- backend mobile-native docs aidlc-docs
```

## 5. APK 수동 QA

1. 기존 앱과 새 APK의 서명이 다르면 기존 앱을 삭제한다.
2. APK를 설치하고 앱을 완전히 종료한 뒤 다시 실행한다.
3. 소셜 로그인과 앱 딥링크 복귀를 확인한다.
4. 사건 생성 → 업로드 → 분석 → 챗봇 순서로 검증한다.
5. 한국어·영어·베트남어로 챗봇을 테스트한다.
6. 커뮤니티 제목·본문·댓글 번역과 안전검사를 확인한다.
7. 로그아웃 후 보호 화면 접근과 재로그인을 확인한다.

## 6. PR 전 확인 사항

- `app.json`의 `apiBase`, Expo `owner`, `projectId`가 공식 값인지 확인한다.
- 임시 EAS 계정이나 로컬 `10.0.2.2` 설정을 커밋하지 않는다.
- 실제 OAuth Client의 callback URL과 백엔드 환경변수가 일치해야 한다.
- 테스트용 JWT, AWS 키, OAuth Client Secret을 문서나 Git에 남기지 않는다.
- Terraform 변경은 코드 리뷰 후 인프라 담당자가 plan/apply한다.

## 7. 알려진 한계

- 로그아웃 시 서버 측 JWT revocation은 아직 없다.
- OAuth provider의 계정 세션이 남으면 계정 선택 화면이 생략될 수 있다.
- Expo Go와 APK는 권한·딥링크·네이티브 모듈 동작이 다를 수 있으므로 최종 검증은 APK에서 수행한다.
- Bedrock, RAG, 번역은 운영 환경의 IAM·모델 접근·DB seed 상태에 영향을 받는다.
