# BADA 프로젝트 작업 요약 (2026-06-22)

## 오늘 완료한 작업 전체 목록

---

### 1. AI-DLC 워크플로우 수행 (기획 단계)

| 단계 | 산출물 |
|------|--------|
| 역공학 분석 | 코드베이스 전체 분석 → 8개 문서 (`aidlc-docs/inception/reverse-engineering/`) |
| 요구사항 분석 | 12개 질문 응답 → MVP 요구사항 정의 (`requirements.md`) |
| 실행 계획 | 6유닛 분해, 일정 수립 (`execution-plan.md`) |
| 애플리케이션 설계 | 컴포넌트/서비스/의존성 설계 5개 문서 |
| 유닛 생성 | 6유닛 정의서 + 의존성 매트릭스 + 요구사항 매핑 |

---

### 2. 코드 생성 (구현 단계) — 6개 유닛

| 유닛 | 변경 파일 | 내용 |
|------|----------|------|
| 1. 인프라/보안 | `infra/main.tf`, `variables.tf`, `backend/app/middleware/` | HTTPS(ACM), 보안 헤더, Rate limit, CORS 제한, ALB 로깅, Worker 기동, Frontend ECR/TG, Route 53 |
| 2. 인증 | (변경 없음) | 이미 구현 완료 확인 — 설정 전환만 필요 |
| 3. Worker | `worker/handlers/`, `worker/db.py`, `worker/Dockerfile` | DB 직접 접근(2단계), STT(Transcribe) 구현, consumer.py CMD |
| 4. PDF | `worker/services/pdf_generator.py`, `templates/` | WeasyPrint Evidence Pack, 다국어 폰트 |
| 5. Frontend | `frontend/` 전체 | Next.js 15, Tailwind, next-intl, ECS 배포 |
| 6. PBT | `worker/tests/test_pbt_*.py` | Hypothesis 4모듈 (wage, deductions, geofence, guardrails) |

---

### 3. 모니터링 스택 구축

| 구성 | 파일 | 설명 |
|------|------|------|
| Terraform | `infra/monitoring.tf` | Prometheus + Grafana ECS, EFS, ALB 라우팅, Route 53 |
| Backend 메트릭 | `backend/app/middleware/prometheus.py` | `/metrics` 엔드포인트 (요청수, 응답시간, 에러율) |
| Prometheus 설정 | `monitoring/prometheus/prometheus.yml` | scrape 타겟 설정 |
| Grafana 대시보드 | `monitoring/grafana/provisioning/` | 자동 프로비저닝 (Overview 대시보드) |
| 설계 문서 | `aidlc-docs/construction/monitoring/monitoring-design.md` | 아키텍처 + 비용 |

**접속:** `https://monitor.badasoft.com` (admin / Secrets Manager 값)

---

### 4. 모바일 앱 (Capacitor)

| 파일 | 내용 |
|------|------|
| `mobile/package.json` | 백그라운드 GPS 플러그인 추가 |
| `mobile/capacitor.config.json` | 프로덕션 서버 URL 설정 |
| `frontend/src/lib/gps.ts` | GPS 백그라운드(네이티브) + 포그라운드(웹) 서비스 |
| `frontend/src/app/[locale]/cases/[id]/gps/page.tsx` | GPS 추적 UI |
| `aidlc-docs/construction/mobile/mobile-setup.md` | 설정 가이드 |

---

### 5. CI/CD 수정

| 수정 | 이유 |
|------|------|
| `ci.yml` — worker requirements 설치 추가 | hypothesis import 실패 |
| `deploy-dev-frontend.yml` — 수동 실행 전환 | ECR 없는 상태에서 자동 트리거 방지 |
| `deploy-dev-frontend.yml` — Role ARN env 참조 | secrets 대신 env 직접 참조 (Backend과 동일) |

---

### 6. 배포 중 해결한 이슈

| 이슈 | 원인 | 해결 |
|------|------|------|
| CI 실패 | worker requirements 미설치 | ci.yml에 `pip install -r worker/requirements.txt` 추가 |
| Frontend CD 인증 실패 | `secrets.AWS_DEPLOY_ROLE_ARN` 미등록 | `env.AWS_ROLE_ARN` 직접 참조로 변경 |
| Worker Docker 빌드 실패 | `libgdk-pixbuf2.0-0` 패키지명 오류 | `libgdk-pixbuf-2.0-0`으로 수정, emoji 폰트 제거 |
| Frontend `npm ci` 실패 | package-lock.json 없음 | `npm install`로 변경 |
| Frontend 빌드 실패 | `@transistorsoft` 유료 패키지 | 네이티브 전용 패키지 frontend에서 제거 |
| Frontend TS 에러 | 모듈 타입 해석 실패 | 변수 우회 + `webpackIgnore` 적용 |
| `www.badasoft.com` 접속 불가 | Route 53 A 레코드 누락 | Terraform에 www 레코드 추가 |
| Grafana 로그인 실패 | Secrets Manager 비밀번호 미확인 | AWS 콘솔에서 시크릿 값 확인 |

---

## 현재 배포 상태

| 서비스 | URL | 상태 |
|--------|-----|------|
| Backend API | `https://api.badasoft.com` | ✅ 동작 |
| Frontend | `https://badasoft.com` | ✅ 배포 완료 |
| Grafana | `https://monitor.badasoft.com` | ✅ 대시보드 동작 |
| `www.badasoft.com` | — | ⏳ terraform apply 대기 |
| Worker | ECS 태스크 | ⏳ 인프라 담당 확인 중 |

---

## 테스트 결과

| 구분 | 결과 |
|------|------|
| Backend 단위 테스트 | 47 passed ✅ |
| Worker 단위 테스트 | 155 passed ✅ |
| Worker PBT (Hypothesis) | 13 passed ✅ |
| **합계** | **215 passed** |

---

## Git 커밋 이력 (develop)

```
d8634c9  인프라: www.badasoft.com Route 53 A 레코드 추가
998f7dd  Frontend: 네이티브 전용 패키지 제거 (모바일에서만 사용)
906fd79  Frontend Dockerfile: npm ci → npm install
c5b6bf8  GPS: TypeScript 모듈 해석 우회 (네이티브 플러그인 빌드 에러 수정)
30ae6bc  GPS: 네이티브 플러그인 import를 webpackIgnore로 빌드 시 무시
a53acb2  모바일 앱: Capacitor + GPS 백그라운드 추적 구현
cd83260  문서: 팀 역할 배분 (5인, 6/22 기준)
0e058ef  모니터링 추가: Prometheus + Grafana (ECS Fargate, EFS 영속화)
0b174e6  Worker Dockerfile 수정: apt 패키지명 오류 수정 (slim 이미지 호환)
45ccc24  프론트엔드 배포 수정: OIDC Role ARN을 env로 직접 참조
6ec1e75  문서: 모니터링 작업 로그 추가
045ede2  프론트엔드 배포: 인프라 준비 전까지 수동 실행으로 변경
2b3473f  CI 수정: worker 의존성(hypothesis) 설치 추가
3cbd177  AI-DLC 문서 추가: 역공학 분석, 요구사항, 설계, 유닛 정의, 빌드 지침
0da25b6  MVP 프로덕션 완성: HTTPS, 보안, Worker 2단계, PDF, Frontend, PBT
```

---

## 다음 작업 (팀별)

`aidlc-docs/team-task-distribution.md` 참고
