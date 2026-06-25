# BADA Mobile Frontend E2E Test Report

## 목적

이 문서는 현재 `feature/mobile-e2e-polish` 코드 상태에서 모바일 프론트엔드가 사용자 관점의 핵심 흐름을 충족하는지 확인한 결과를 정리한다.

범위는 Cognito 로그인, Bearer 토큰 기반 API 호출, 사건 생성, 사건 조회, 증거 업로드, AI 챗봇 호출, 모바일 번들 검증이다.

## 사용자 관점 테스트 시나리오

### 1. 앱 진입 및 로그인

- 앱 실행 시 로그인 화면 진입
- Google 로그인 버튼을 통해 Cognito 로그인 시작
- Cognito 콜백 이후 모바일 딥링크(`bada://auth` 또는 Expo 링크)로 앱 복귀
- 앱이 받은 토큰을 저장
- 단순 토큰 존재 여부가 아니라 `GET /auth/me` 호출로 실제 인증 상태 확인

상태: 구현 완료, 자동 테스트로 콜백 계약 검증 완료

주의: 실제 `badasoft.com` 배포 환경에서의 Google 로그인 최종 E2E는 PR merge와 CD 배포 이후 확인해야 한다.

### 2. Bearer Token API 호출

- 로그인 후 모바일 API 클라이언트가 저장된 토큰을 읽음
- API 요청 시 `Authorization: Bearer <token>` 헤더 자동 주입
- 인증이 필요한 API에서 401이 아닌 정상 응답을 기대

상태: 구현 완료, 백엔드 테스트 통과

### 3. 사건 생성 및 목록 확인

- 사용자가 새 사건을 생성
- 사건 목록 화면에서 생성된 사건 확인
- 사건 상세 화면으로 이동

상태: 구현 완료

### 4. 증거 업로드

- 사건 상세 또는 업로드 화면에서 파일 선택
- 모바일 앱은 `POST /cases/{case_id}/evidences/upload` multipart API로 업로드
- 업로드 후 사건 상세 또는 목록에서 자료 흐름을 이어갈 수 있음

상태: 구현 완료, 업로드 API 계약 반영 완료

### 5. AI 챗봇 호출

- 사건에 연결된 챗봇 화면 진입
- 사용자가 상담 준비 질문 입력
- UUID `case_id`를 임의 숫자 `1`로 바꾸지 않고 그대로 전달
- 백엔드 챗봇 API와 연결되는 흐름 유지

상태: 구현 완료

### 6. 로그아웃 및 세션 정리

- 앱에서 로그아웃 시 저장 토큰 제거
- Cognito 로그아웃 URL로 이동 가능
- 다음 로그인 때 계정 선택 흐름을 다시 시작할 수 있음

상태: 구현 완료

## 프론트엔드 요구사항 충족 체크리스트

| 요구사항 | 충족 여부 | 구현 내용 |
| --- | --- | --- |
| Cognito 로그인 연동 | 완료 | `/auth/cognito/login` 시작, callback 후 모바일 딥링크로 토큰 반환 |
| 토큰 저장 | 완료 | 모바일 SecureStore 기반 토큰 저장/조회/삭제 |
| API Bearer 호출 | 완료 | 공통 API 클라이언트에서 `Authorization: Bearer` 자동 주입 |
| `/auth/me` 인증 확인 | 완료 | 홈 진입 시 실제 인증 API로 로그인 상태 확인 |
| 사건 생성 E2E | 완료 | 사건 생성 화면과 API 연결 |
| 사건 목록/상세 | 완료 | 목록, 상세 화면 흐름 구성 |
| 증거 업로드 E2E | 완료 | multipart 업로드 API 경로로 통일 |
| AI 챗봇 화면 | 완료 | 채팅 UI와 백엔드 챗봇 API 연결 |
| UUID case_id 처리 | 완료 | 챗봇 호출에서 UUID를 숫자 샘플 ID로 바꾸던 문제 제거 |
| 모바일 앱 번들 검증 | 완료 | Expo Android export smoke 통과 |
| TypeScript 정합성 | 완료 | `tsc --noEmit` 통과 |
| 백엔드 회귀 테스트 | 완료 | `pytest -q` 전체 통과 |
| 충돌 마커 제거 | 완료 | `<<<<<<<`, `=======`, `>>>>>>>` 실제 충돌 마커 없음 |
| 배포 환경 실로그인 검증 | 대기 | PR merge 및 CD 배포 후 `badasoft.com` 기준 최종 확인 필요 |

## 검증 명령 및 결과

### Git 상태 확인

```bash
git status --short
```

결과: 모바일 E2E, Cognito, 업로드, 챗봇 관련 변경 파일이 작업트리에 남아 있음.

### Whitespace 검사

```bash
git diff --check
```

결과: 통과

### 충돌 마커 검사

```bash
rg -n '^(<<<<<<<|=======|>>>>>>>)' backend mobile-native docs
```

결과: 충돌 마커 없음

### 모바일 TypeScript 검사

```bash
cd mobile-native
npm exec tsc -- --noEmit
```

결과: 통과

### Expo Android Export Smoke

```bash
cd mobile-native
npm exec expo -- export --platform android --no-bytecode --output-dir .expo-export-check
```

결과: 통과

### 백엔드 전체 테스트

```bash
cd backend
python -m pytest -q
```

결과:

```text
53 passed, 3 warnings in 28.63s
```

## PR 전 수동 QA 순서

### 1. 백엔드 실행

```bash
cd ~/BADA/BADA-mobile-native/backend
source .venv/Scripts/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Expo 실행

```bash
cd ~/BADA/BADA-mobile-native/mobile-native
npx expo start -c
```

### 3. 앱에서 확인할 것

1. 앱 실행
2. Google 로그인 시작
3. Cognito 로그인 완료 후 앱으로 복귀
4. 홈 화면에서 사용자 정보 확인
5. 새 사건 생성
6. 사건 목록에서 생성된 사건 확인
7. 사건 상세 진입
8. 증거 파일 업로드
9. 챗봇에서 사건 관련 질문 전송
10. 로그아웃 후 재로그인 흐름 확인

## 남은 확인 사항

- 실제 운영 도메인 `badasoft.com` 기준 Google 로그인 E2E는 PR merge와 CD 배포 이후 재검증 필요
- Cognito callback/logout URL은 인프라 환경값과 일치해야 함
- 실제 Android 기기에서 파일 선택 권한, 카메라 권한, 업로드 UX 확인 필요
- 인프라 `terraform apply`는 이 작업에서 실행하지 않았음
