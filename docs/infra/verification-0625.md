# 인프라 검증 결과 및 요청사항 (2026-06-25)

> PR #65 `feature/agent` + PR #66 `feature/mobile-native` 머지 후 인프라 재검증.

---

## 1. 인프라 상태 (06/24 15:00 검증)

| 항목 | 상태 |
|------|------|
| Terraform plan | No changes |
| Backend ECS | desired=1/running=1, Task :44 |
| Worker ECS | desired=1/running=1, Task :18 |
| Frontend ECS | desired=1/running=1, Task :3 |
| Prometheus ECS | desired=1/running=1, Task :2 |
| Grafana ECS | desired=1/running=1, Task :1 |
| `https://badasoft.com/api/health` | ✅ 200 |
| `https://api.badasoft.com/health` | ✅ 200 |
| `https://monitor.badasoft.com/api/health` | ✅ 200 |
| ALB Target Group | Frontend/Backend/Grafana 모두 healthy |
| CloudWatch Alarm 14개 | 모두 OK |
| SQS Main Queue / DLQ | 0 |
| 최근 로그 오류 패턴 | 없음 |

**결론**: 인프라 정상.

### 1.1 최신 보정 (06/25 모니터링 provisioning 후)

| 항목 | 상태 |
|------|------|
| Terraform plan | No changes |
| Backend ECS | desired=1/running=1, Task :49 |
| Worker ECS | desired=1/running=1, Task :19 |
| Frontend ECS | desired=1/running=1, Task :3 |
| Prometheus ECS | desired=1/running=1, Task :2 |
| Grafana ECS | desired=1/running=1, Task :6 |
| Grafana Alert | Contact Point `BADA-SNS`, Rule G1~G8 8개, Notification Policy receiver `BADA-SNS` |

**남은 확인**: Grafana Alert의 실제 이메일 수신과 OK 복구 메일은 수신함 기준으로 확인한다.

---

## 2. 백엔드 요청사항 — 구현 현황

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| 2-1 | 소셜 OAuth 모바일 딥링크 (`bada://auth#token=`) | ⏳ 진행 | `/auth/{provider}/callback` 분기 필요 |
| 2-2 | AI 챗봇 `case_id` UUID 수용 | ✅ 완료 (6/24) | `a67fa14` — 미지정 시 일반 상담 |
| 2-3 | `GET /cases/{id}/report.pdf` presigned GET 302 | ✅ 완료 (6/24) | `3640e2c` — 미생성 시 404 |
| 2-4 | Presigned Upload Content-Type 정합 | ✅ 완료 (6/24) | `a51a529` — content_type 옵셔널+화이트리스트 |

### 2-1 상세: 소셜 OAuth 딥링크 (진행)

> 팀 결정(6/25): Cognito 제거 → 구글/카카오/네이버 소셜 OAuth.

**현재**: 웹 로그인 성공 → `#token=` 해시로 프론트에 전달.
**필요**: 모바일이 `redirect_uri=bada://auth`로 요청 시 → callback에서 `bada://auth#token=<JWT>` 302 redirect.

구현 방안:
- `/auth/{provider}/login` (provider=google|kakao|naver) 호출 시 `state`에 원래 redirect_uri 보존
- 소셜 OAuth callback 성공 후 state 파싱 → 앱 스킴이면 앱으로 redirect
- 기존 웹 `#token=` 흐름 무영향
- 각 provider Redirect URI는 운영(`https://api.badasoft.com/auth/{provider}/callback`) 기준, `AUTH_MODE`를 cognito→oauth/jwt로 전환

진행 현황:
- ✅ 모바일(앱): `features/auth/api.ts` `buildAuthUrl` Cognito 제거 → `/auth/{provider}/login?redirect_uri=bada://auth` 호출로 전환, `logout` Hosted UI 호출 제거 (tsc 통과)
- ✅ 백엔드: `social_callback` 딥링크 분기는 **이미 구현돼 있었음**(state에 redirect_uri 보존 → `bada://auth?token=`). Cognito 코드 전면 제거(라우터/deps/config/service/test/PyJWT), 로컬 부팅·설정 로드 검증 완료
- ⏳ **prod 컷오버(인프라)**: `AUTH_MODE=oauth` + 3 provider 시크릿 + `JWT_SECRET` + `api.badasoft.com` 콜백 (인프라가 prod tfvars로 plan→apply)

---

## 3. 모바일 담당 확인 필요사항

| # | 항목 | 확인 필요 |
|---|------|-----------|
| 1 | 실행 방식 | Expo Go / 개발빌드 APK / EAS preview APK |
| 2 | 앱 식별 | package=`com.bada.app`, scheme=`bada`, redirect=`bada://auth` |
| 3 | E2E 테스트 시나리오 | 로그인→사건→증거→분석→결과 |
| 4 | 업로드 방식 | 네이티브 S3 direct PUT (CORS 불필요) vs Expo Web (CORS 필요) |

**참고**: 순수 네이티브 앱은 브라우저가 아니므로 S3 CORS가 blocker가 아님. Expo Web 검증도 필요하면 S3 CORS 추가 필요.

---

## 4. 프론트엔드 담당 요청사항

- `feature/app-first-frontend-ui` 브랜치 → `develop` PR 생성 필요
- PR merge 후 인프라 검증 항목:
  - Frontend ECS 새 Task revision 배포
  - ALB healthy
  - CORS/Auth 오류 여부
  - 소셜 OAuth(구글/카카오/네이버) callback/logout URL 정합성
  - Evidence S3 업로드 정상 동작

---

## 5. GPS/Agent/OCR 담당 요청사항

Worker E2E 검증(SQS → Worker → Bedrock → RDS → S3 Report)에 필요:

1. Bedrock 실호출 테스트 사건 ID
2. 입력 파일 또는 테스트 증거
3. 예상 OCR/분석 결과
4. Worker 로그 성공 패턴
5. RDS 저장 결과 필드
6. S3 Report PDF 생성 여부

### 5.1 진행 상황 (에이전트 4단계 OCR 트리거 연결)

- ✅ 네이티브 앱 에이전트 스캔 → 업로드 시 `category=auto`로 전송, 서버 classify가 형태 판별 후 적합한 프롬프트로 OCR
- ✅ 업로드 완료 후 `/extract` fire-and-forget 호출 추가 → Bedrock OCR 즉시 트리거 (분석 시 Worker가 pending OCR 자동 처리하는 폴백도 유지)
- ✅ 스캔 기간 필터 종료일을 `work_end_date` → **현재 시점**으로 수정 → 퇴직 후 캡처한 카톡·명세서도 수집됨 (0개 수집 버그 해결)
- ⏳ 배포 후 CloudWatch Worker 로그에서 `Bedrock 응답` / `extract_ocr` 키워드로 실호출 최종 확인

---

## 6. 모니터링 담당 요청사항

인프라 준비 완료: Grafana ECS, Prometheus ECS, CloudWatch datasource, SNS Email Topic, Grafana Task Role SNS Publish 권한, `BADA-SNS` Contact Point, G1~G8 Alert Rule, `BADA-SNS` Notification Policy.

Grafana Alert 완성에 남은 확인:

1. 이메일 실수신 확인
2. OK 복구 메일 확인
3. 실제 운영 임계치 튜닝 필요 여부
4. Dashboard JSON 최종본

---

## 7. E2E 검증 순서 (각 담당 산출물 수령 후)

1. 모바일 로그인 E2E (딥링크 구현 후)
2. 사건 생성 E2E
3. 증거 업로드 E2E
4. 분석/Worker/Bedrock/PDF E2E
5. Grafana Alert 수신 검증
6. 최종 인프라 게이트 재검증
