# 컴포넌트 메서드 시그니처

## 1. Frontend (Next.js)

### 페이지 (App Router)
| 경로 | 목적 |
|------|------|
| `/[locale]` | 랜딩/로그인 |
| `/[locale]/cases` | 사건 목록 |
| `/[locale]/cases/new` | 사건 생성 |
| `/[locale]/cases/[id]` | 사건 상세 (증거, 분석, 타임라인, GPS) |
| `/[locale]/cases/[id]/upload` | 증거 업로드 |
| `/[locale]/cases/[id]/result` | 분석 결과 |
| `/[locale]/cases/[id]/gps` | GPS 지도뷰 |
| `/[locale]/community` | 커뮤니티 게시판 |
| `/[locale]/chat` | AI 챗봇 |

### 주요 클라이언트 모듈
| 모듈 | 메서드 | 설명 |
|------|--------|------|
| `lib/api.ts` | `fetchApi(path, options)` → `Promise<T>` | ALB API 호출 래퍼 (토큰 자동 주입) |
| `lib/auth.ts` | `login(provider)` → redirect | Cognito/소셜 로그인 시작 |
| `lib/auth.ts` | `handleCallback(code)` → `TokenSet` | 인증 코드 → 토큰 교환 |
| `lib/auth.ts` | `getAccessToken()` → `string \| null` | 저장된 Access Token 반환 |
| `lib/auth.ts` | `logout()` → redirect | 토큰 삭제 + Cognito 로그아웃 |

## 2. Backend API (보안 강화 부분)

### 신규/변경 메서드
| 모듈 | 메서드 | 설명 |
|------|--------|------|
| `deps.py` | `verify_cognito_token(token: str)` → `dict` | Cognito JWKS RS256 검증 → claims 반환 |
| `deps.py` | `get_current_user(...)` → `User` | Cognito 모드에서 Access Token 검증 |
| `middleware/security.py` (신규) | `SecurityHeadersMiddleware` | CSP, HSTS, X-Frame 등 보안 헤더 주입 |
| `middleware/rate_limit.py` (신규) | `RateLimitMiddleware` | IP 기반 Rate limiting (인메모리/Redis 없이 단순 구현) |
| `services/queue.py` | `publish_transcribe(evidence_id, s3_key, lang)` | 음성 전사 SQS 메시지 발행 |

## 3. Worker (2단계 전환)

### 변경 메서드
| 모듈 | 메서드 | 설명 |
|------|--------|------|
| `handlers/analysis.py` | `handle(message: dict)` → `None` | **변경**: DB 직접 접근하여 분석 수행 (Backend HTTP 호출 제거) |
| `handlers/transcription.py` | `handle(message: dict)` → `None` | **구현**: S3 → Transcribe → Evidence.ocr_text 저장 |
| `db.py` (신규) | `get_db_session()` → `Session` | Worker용 SQLAlchemy 세션 팩토리 |
| `services/pdf_generator.py` (신규) | `generate_evidence_pack(case_id, lang)` → `str` | WeasyPrint PDF 생성 → S3 저장 → s3_key 반환 |

### 분석 파이프라인 (process_case 변경)
| 단계 | 입력 | 출력 | 저장 |
|------|------|------|------|
| 1. OCR | Evidence 이미지 | 텍스트 + 엔티티 | Evidence.ocr_text, extracted_entities |
| 2. 규칙 분석 | ctx(엔티티, GPS 등) | 차액/공제/누락/GPS/비교/법적검토 | AnalysisResult |
| 3. 번역 | 타임라인 + 결과 텍스트 | 번역문 | TranslationPair |
| 4. 타임라인 | 이벤트 목록 | 정렬 + 문장화 | TimelineEvent |
| 5. 요약 | 타임라인 설명 | 요약문 | AnalysisResult.timeline_summary |
| 6. PDF | 분석 결과 전체 | PDF 파일 | S3 + AnalysisResult.pdf_ko_s3_key |
| 7. 상태 갱신 | - | - | Case.status = 'completed' |

## 4. Infrastructure (신규 리소스)

### Terraform 신규 리소스
| 리소스 | 목적 |
|--------|------|
| `aws_acm_certificate` | HTTPS 인증서 (도메인 검증) |
| `aws_lb_listener` (443) | HTTPS listener |
| `aws_lb_listener_rule` | 호스트 기반 라우팅 (api.*/프론트) |
| `aws_ecr_repository.frontend` | Frontend 이미지 저장소 |
| `aws_ecs_task_definition.frontend` | Frontend ECS 태스크 |
| `aws_ecs_service.frontend` | Frontend 서비스 |
| `aws_route53_zone` / `record` | 도메인 DNS (준비 시) |
| `aws_lb_target_group.frontend` | Frontend 헬스체크 |
