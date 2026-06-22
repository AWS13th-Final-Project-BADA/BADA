# 애플리케이션 설계 (통합)

## 설계 결정 요약

| 결정 항목 | 선택 | 근거 |
|-----------|------|------|
| Frontend 배포 | ECS Fargate (SSR) | SEO, 서버 컴포넌트, next-intl SSR 다국어 |
| API 통신 | ALB 직접 호출 (CORS) | 카카오/모바일 동일 API, 단순, 비용 절감 |
| 인증 토큰 | Cognito Access Token 직접 (JWKS 검증) | 표준 OAuth2, 소셜 IdP 통합, 상태 비저장 |
| Worker DB | 직접 접근 (2단계) | Backend 경유 제거, 성능 향상, 독립 실행 |
| 도메인 구조 | 서브도메인 분리 (bada.kr + api.bada.kr) | 관심사 분리, CORS 명확, 독립 스케일링 |

---

## 아키텍처 다이어그램 (목표 상태)

```
                    사용자 (브라우저/카카오/모바일)
                              │
                              ▼
                    ┌─────────────────────┐
                    │   ALB (HTTPS/443)   │
                    │  ACM 인증서 적용     │
                    └──────┬──────┬───────┘
                           │      │
              호스트 라우팅  │      │  호스트 라우팅
              bada.kr      │      │  api.bada.kr
                           ▼      ▼
              ┌────────────┐  ┌────────────┐
              │  Frontend  │  │  Backend   │
              │  (Next.js) │  │  (FastAPI) │
              │  ECS Task  │  │  ECS Task  │
              └────────────┘  └─────┬──────┘
                                    │
                              ┌─────┼─────┐
                              ▼     ▼     ▼
                           ┌────┐ ┌───┐ ┌─────┐
                           │RDS │ │S3 │ │ SQS │
                           └────┘ └───┘ └──┬──┘
                                           │
                                           ▼
                              ┌────────────────────┐
                              │      Worker        │
                              │  (SQS Consumer)    │
                              │  ECS Task          │
                              └────────┬───────────┘
                                       │
                         ┌─────────────┼─────────────┐
                         ▼             ▼             ▼
                      ┌────┐    ┌──────────┐   ┌──────────┐
                      │RDS │    │ Bedrock  │   │Transcribe│
                      └────┘    │ Translate│   └──────────┘
                                └──────────┘
```

---

## 컴포넌트 요약

| 컴포넌트 | 기술 | 배포 | 상태 |
|----------|------|------|------|
| Frontend | Next.js 15 + Tailwind + next-intl | ECS Fargate (bada.kr) | 신규 |
| Backend | FastAPI + SQLAlchemy + Pydantic | ECS Fargate (api.bada.kr) | 보안 강화 |
| Worker | Python SQS Consumer + 규칙엔진 | ECS Fargate | 2단계 전환 + STT + PDF |
| Infra | Terraform | - | HTTPS + Frontend ECS 추가 |
| CI/CD | GitHub Actions | - | Frontend 파이프라인 추가 |

---

## 핵심 변경 사항 (기존 대비)

### Backend
1. `AUTH_MODE=cognito` — Cognito JWKS 토큰 검증으로 전환
2. 보안 미들웨어 추가 (헤더, Rate limit, CORS 도메인 제한)
3. SQS transcribe 메시지 발행 추가
4. Worker 2단계 전환에 따라 `/analyze` 엔드포인트는 SQS 발행 전용으로 변경

### Worker
1. `db.py` 추가 — SQLAlchemy 직접 세션 (DATABASE_URL from Secrets Manager)
2. `handlers/analysis.py` — Backend HTTP 호출 → DB 직접 분석/저장으로 전환
3. `handlers/transcription.py` — Amazon Transcribe 연동 구현
4. `services/pdf_generator.py` — WeasyPrint PDF 생성 추가
5. `Dockerfile` — 다국어 폰트 임베딩 (Noto Sans 패밀리)

### Infrastructure
1. ACM 인증서 + HTTPS listener (443)
2. ALB 호스트 기반 라우팅 규칙 (bada.kr → Frontend, api.bada.kr → Backend)
3. Frontend ECR + ECS Task Definition + Service
4. Worker `desired_count=0 → 1` 전환
5. Route 53 호스팅 영역 (도메인 구매 시)
6. ALB access logging 활성화

### Frontend (신규)
1. Next.js 15 App Router + TypeScript
2. Tailwind CSS + 반응형 모바일 우선
3. next-intl 다국어 (ko, vi, en)
4. Cognito 인증 클라이언트 (PKCE flow)
5. 모든 화면: 로그인, 사건, 업로드, 결과, GPS, 커뮤니티, 챗봇

---

## 상세 문서 참조

- [컴포넌트 정의](components.md)
- [컴포넌트 메서드](component-methods.md)
- [서비스 계층](services.md)
- [의존성 관계](component-dependency.md)
