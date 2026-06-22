# BADA 팀 역할 배분 (6/22 기준)

## 현재 진행 상태

| 구분 | 상태 |
|------|------|
| AWS 인프라 (ECS, ALB, RDS, S3, SQS, Route53) | ✅ 배포 완료 |
| Backend API (FastAPI, 보안, 인증) | ✅ 배포 완료 |
| Worker 분석 파이프라인 (규칙엔진, DB 직접, PDF) | ✅ 배포 완료 |
| HTTPS + 도메인 (badasoft.com) | ✅ 적용 완료 |
| Frontend (Next.js) | 🔄 CD 배포 진행 중 |
| 모바일 앱 (Capacitor) | ⏳ 코드 준비됨, 빌드 필요 |
| 모니터링 (Prometheus + Grafana) | ⏳ Terraform 코드 준비, apply 대기 |
| GPS 백그라운드 추적 | ⏳ 코드 준비됨, 네이티브 빌드 후 검증 필요 |
| 음성 전사 (STT) | ⏳ 코드 준비됨, E2E 검증 필요 |

---

## 팀원별 담당 업무

### 1️⃣ 인프라 담당

**핵심 역할**: AWS 인프라 운영, Terraform 관리, 배포 파이프라인

| 우선순위 | 업무 | 상세 | 예상 기간 |
|----------|------|------|----------|
| P0 | Frontend ECS 안정화 | Task Definition, 헬스체크, 로그 확인 | 6/23 |
| P0 | Monitoring 활성화 | `monitoring_enabled=true` → terraform apply | 6/23 |
| P1 | Cognito callback URL HTTPS 전환 | terraform.tfvars 업데이트 + apply | 6/23 |
| P1 | Worker 환경변수 검증 | PROVIDER_MODE=aws, DATABASE_URL, SQS_QUEUE_URL 확인 | 6/24 |
| P2 | 모바일 앱 배포 인프라 | 필요시 S3/CloudFront 또는 앱 배포 지원 | 6/25~ |
| P2 | 비용 모니터링 | AWS Budgets 알림 확인, Bedrock 사용량 체크 | 상시 |

**관련 파일**: `infra/*.tf`, `.github/workflows/deploy-*.yml`, `terraform.tfvars`

---

### 2️⃣ 프론트엔드 담당

**핵심 역할**: Next.js 웹앱 완성, UI/UX, 다국어

| 우선순위 | 업무 | 상세 | 예상 기간 |
|----------|------|------|----------|
| P0 | 빌드 에러 해결 | package-lock.json 생성, next-intl 버전 호환 | 6/23 |
| P0 | Cognito 로그인 연동 | 로그인 → 토큰 저장 → API 호출 E2E | 6/23~24 |
| P1 | 핵심 화면 완성 | 사건 생성/상세, 증거 업로드, 분석 결과, 타임라인 | 6/24~25 |
| P1 | 커뮤니티 게시판 화면 | 글 목록/작성/댓글/번역 | 6/25~26 |
| P1 | AI 챗봇 화면 | 채팅 UI, 메시지 송수신 | 6/25~26 |
| P2 | 모바일 반응형 QA | 모바일 브라우저 레이아웃 검증 | 6/26 |

**관련 파일**: `frontend/src/`, `frontend/locales/`

---

### 3️⃣ 모바일 앱 담당

**핵심 역할**: Capacitor 네이티브 앱 빌드, GPS 네이티브 통합, 앱 배포

| 우선순위 | 업무 | 상세 | 예상 기간 |
|----------|------|------|----------|
| P0 | Android 프로젝트 초기화 | `npx cap add android`, 빌드 환경 세팅 | 6/23 |
| P0 | 앱 빌드 + 에뮬레이터 실행 | Next.js → Capacitor sync → 실행 확인 | 6/23~24 |
| P1 | GPS 백그라운드 플러그인 설정 | Android 권한, 백그라운드 동작 검증 | 6/24~25 |
| P1 | 네이티브 UI 개선 | 스플래시 스크린, 상태바, 뒤로가기 처리 | 6/25 |
| P2 | APK 빌드 | 릴리즈 빌드, 팀 테스트용 배포 | 6/26 |
| P2 | iOS 빌드 (Mac 있을 시) | Xcode 빌드 | 6/26~ |

**관련 파일**: `mobile/`, `frontend/src/lib/gps.ts`

---

### 4️⃣ GPS + Agent + OCR 담당

**핵심 역할**: GPS 고도화, AI Agent 개발, Worker OCR 안정화

| 우선순위 | 업무 | 상세 | 예상 기간 |
|----------|------|------|----------|
| P0 | OCR Worker E2E 검증 | Bedrock Claude Vision 실제 호출 → 엔티티 추출 확인 | 6/23 |
| P0 | Worker 분석 E2E | SQS 메시지 → 분석 → DB 저장 → status=completed | 6/23~24 |
| P1 | GPS 고도화 | 교차검증 로직 검증, 지연 업로드 처리, 일별 요약 | 6/24~25 |
| P1 | Agent 개발 | AI 챗봇 RAG 연동, 의도 분류 개선, Bedrock 실호출 | 6/25~26 |
| P2 | PDF 렌더링 검증 | 한국어/베트남어 Evidence Pack 출력 확인 | 6/26 |
| P2 | 카카오톡 봇 연동 테스트 | /kakao/skill 엔드포인트 동작 확인 | 6/26 |

**관련 파일**: `worker/`, `backend/app/services/ai_chat_orchestrator.py`, `backend/app/routers/gps.py`

---

### 5️⃣ 모니터링 + 음성 전사 담당 (나)

**핵심 역할**: Grafana 대시보드 구축, Prometheus 연동, STT 기능 검증

| 우선순위 | 업무 | 상세 | 예상 기간 |
|----------|------|------|----------|
| P0 | Grafana 접속 확인 | monitor.badasoft.com 접속, 초기 로그인 | 6/23 |
| P0 | Prometheus → Backend 연결 | scrape 타겟 설정, /metrics 수집 확인 | 6/23~24 |
| P1 | 대시보드 구축 | Overview, Backend, Worker, Infrastructure 패널 | 6/24~25 |
| P1 | 음성 전사 E2E 검증 | 음성 파일 업로드 → SQS → Transcribe → 텍스트 저장 | 6/24~25 |
| P1 | CloudWatch 데이터소스 연동 | AWS 메트릭(ECS CPU, RDS, SQS 깊이) Grafana 표시 | 6/25 |
| P2 | 알림 설정 | Grafana Alert → SNS/이메일 | 6/26 |
| P2 | PBT CI 확인 | Hypothesis 테스트 CI 통과, 시드 기록 확인 | 6/26 |

**관련 파일**: `monitoring/`, `backend/app/middleware/prometheus.py`, `worker/handlers/transcription.py`

---

## 공통 일정

| 날짜 | 마일스톤 |
|------|----------|
| 6/23(화) | Frontend 빌드 성공 + Worker E2E 1건 + Monitoring 접속 |
| 6/24(수) | Cognito 로그인 E2E + 모바일 앱 에뮬레이터 실행 |
| 6/25(목) | 전체 흐름 동작 (업로드 → 분석 → 결과 → PDF) |
| 6/26(금) | GPS 백그라운드 검증 + Agent 동작 + 대시보드 완성 |
| 6/27~28 | **주말 휴무** |
| 6/29(월) | 통합 테스트 + 데모 리허설 |
| 6/30(화) | 최종 검증 + 배포 안정화 |

---

## Phase 2 (기능 완료 후 진행)

| 업무 | 담당 |
|------|------|
| 테스트 시나리오 작성 | 전원 |
| 다국어 번역 검증 (vi, en) | 다국어 담당 + 전원 리뷰 |
| 데모 시나리오 + 시드 데이터 | PM |
| 평가셋 라벨링 (eval) | 전원 |
| 발표 자료 준비 | PM |

---

## 참고 문서

| 문서 | 위치 |
|------|------|
| 빌드/배포 지침 | `aidlc-docs/construction/build-and-test/` |
| 모니터링 설계 | `aidlc-docs/construction/monitoring/monitoring-design.md` |
| 모바일 앱 설정 | `aidlc-docs/construction/mobile/mobile-setup.md` |
| 인프라 현황 | `docs/infra-implementation-status.md` |
| 역할 분담 원본 | `docs/OWNERSHIP.md` |
| 아키텍처 규칙 | `.kiro/steering/architecture.md` |
