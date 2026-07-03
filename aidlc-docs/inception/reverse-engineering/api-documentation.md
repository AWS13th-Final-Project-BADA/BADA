# API Documentation

## REST APIs

All endpoints are prefixed based on their router registration in `main.py`.

### Cases (`/cases`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/cases` | 사건 생성 (workplace, employer, wage, hours, issue_types) |
| GET | `/cases` | 사용자의 사건 목록 조회 |
| GET | `/cases/{case_id}` | 사건 상세 조회 |

### Evidences (`/cases/{case_id}/evidences`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/cases/{id}/evidences` | Presigned PUT URL 발급 + 증거 레코드 생성 (body: file_name, file_type, category, content_type?) — content_type 지정 시 MIME 화이트리스트 검증 |
| GET | `/cases/{id}/evidences` | 사건의 증거 목록 조회 |
| DELETE | `/cases/{id}/evidences/{eid}` | 증거 삭제 |
| POST | `/cases/{id}/evidences/manual` | 카테고리만 등록 (분류 전용) |
| POST | `/cases/{id}/evidences/upload` | 파일 업로드 (multipart: category + file) |
| POST | `/cases/{id}/evidences/scan` | 카메라 스캔 업로드 |
| POST | `/cases/{id}/evidences/agent-upload` | 에이전트(카카오봇) 경유 업로드 |
| POST | `/cases/{id}/evidences/assess` | 증거 사전 평가 (OCR + 유용성 판정) |
| POST | `/cases/{id}/evidences/extract` | OCR 추출 실행 |
| GET | `/cases/{id}/evidences/extract` | OCR 추출 상태 조회 |
| PATCH | `/cases/{id}/evidences/{eid}/entities` | 추출 엔티티 수정 (Human-in-the-loop) |
| POST | `/cases/{id}/evidences/{eid}/restore` | 삭제된 증거 복원 |

### Analysis (`/cases/{case_id}`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/cases/{id}/analyze` | 분석 실행 (규칙 기반 차액/공제/타임라인/GPS) |
| GET | `/cases/{id}/analysis` | 분석 결과 재조회 |
| GET | `/cases/{id}/timeline` | 타임라인 이벤트 목록 |
| GET | `/cases/{id}/translation-pairs` | 원문-번역 대조표 |
| GET | `/cases/{id}/missing` | 누락 증거 체크리스트 |
| GET | `/cases/{id}/report.html` | 제출용 HTML 리포트 (Evidence Pack) |
| GET | `/cases/{id}/report.pdf` | 제출용 PDF 다운로드 — S3 presigned GET으로 302 리다이렉트 (lang=ko\|native, 미생성 시 404) |

### GPS (`/cases/{case_id}/gps`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/cases/{id}/gps/workplace` | 근무지(지오펜스) 등록 |
| GET | `/cases/{id}/gps/workplace` | 등록된 근무지 조회 |
| POST | `/cases/{id}/gps/ping` | GPS 좌표 수신 + IN/OUT 즉시 판정 |
| GET | `/cases/{id}/gps/logs` | GPS 로그 전체 조회 |
| GET | `/cases/{id}/gps/summary` | 일별 GPS 요약 (Evidence Pack용) |

### AI Chat (`/chat`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat/messages` | 사건 UUID 기반 상담 준비 답변. JSON·form·query 입력을 지원하며 `case_id` 미지정 시 일반 상담으로 동작 |

요청 핵심 필드:

- `case_id: string | null`: 사건 UUID. 모바일은 숫자 샘플 ID로 변환하지 않는다.
- `message: string`: 사용자 질문. `text`, `question` 별칭도 허용한다.
- `language: string`: 기본값 `auto`; 질문 언어를 감지해 같은 언어로 답변한다.
- `session_id: int | null`: 선택 입력.

응답은 `answer`, `intent`, `risk_level`, `ai_provider`, `used_case_context`, `used_rag`, `guardrail_result`, `fallback_used`, `sources`, `next_actions`, `disclaimer`를 포함한다. RAG 출처에는 기관·문서명·섹션·발췌문·검색 방식이 포함되며 모바일에서 상세 모달로 확인한다.

### Auth (`/auth`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/{provider}/login` | 소셜 OAuth 시작(`kakao`, `google`, `naver`). 선택적인 `redirect_uri`를 검증 후 state에 보존 |
| GET | `/auth/{provider}/callback` | provider code 교환 → 사용자 upsert → 자체 JWT 발급 → 웹 또는 앱 딥링크 복귀 |
| POST | `/auth/kakao/link-code` | 로그인 사용자의 카카오톡 채널 연동 코드 발급 |
| GET | `/auth/me` | Bearer JWT로 현재 사용자 정보 조회 |
| POST | `/auth/logout` | 성공 응답 반환. 실제 로그아웃은 클라이언트 SecureStore 토큰 삭제에 기반 |

현재 운영 인증은 직접 소셜 OAuth + 백엔드 자체 HS256 JWT(기본 7일 만료) 방식이다. 앱은 `redirect_uri=bada://auth` 또는 Expo 링크를 전달하고, 백엔드는 허용된 scheme·host만 복귀 주소로 사용한다. 모바일 API 클라이언트는 401 응답 시 저장 토큰을 삭제하고 로그인 화면으로 이동한다. 서버 측 refresh token과 JWT revocation은 아직 구현되지 않았다.

### Kakao Skill (`/kakao`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/kakao/skill` | 카카오톡 스킬 서버 메시지 수신 (대화·증거·GPS·분석 라우팅) |

### Community (`/community`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/community/posts` | 게시글 피드. category, sort, 검색어, 내 글 필터 지원 |
| POST | `/community/posts` | 게시글 작성. 제목·본문 안전검사 적용 |
| GET | `/community/posts/{post_id}` | 게시글 상세 |
| PATCH | `/community/posts/{post_id}` | 작성자 게시글 수정 |
| DELETE | `/community/posts/{post_id}` | 작성자 게시글 soft delete |
| GET | `/community/posts/{post_id}/comments` | 댓글 목록 |
| POST | `/community/posts/{post_id}/comments` | 댓글·답글 작성 및 안전검사 |
| GET | `/community/comments/{comment_id}` | 댓글 상세 |
| PATCH | `/community/comments/{comment_id}` | 작성자 댓글 수정 |
| DELETE | `/community/comments/{comment_id}` | 작성자 댓글 soft delete |
| POST | `/community/reactions` | 게시글·댓글 좋아요, 게시글 저장 토글 |
| POST | `/community/translate` | 게시글 제목·본문 또는 댓글 번역. 캐시된 구형 게시글 번역도 제목을 보정 |
| POST | `/community/reports` | 신고 접수 |
| GET | `/community/reports` | 신고 목록 |
| PATCH | `/community/reports/{report_id}` | 신고 상태 변경 |
| POST | `/community/safety-check` | 개인정보와 법률 판단 요구를 게시 전에 검사 |
| GET | `/community/boards` | 카테고리별 게시판 요약 |

커뮤니티는 사용자 ID로 소유권을 확인한다. 일반 욕설·불만을 일괄 차단하지 않고 개인정보 노출과 법률 단정 요청을 중심으로 차단 또는 수정 안내한다.

### Health/System (루트)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | 헬스체크 (ALB용) |
| GET | `/health/db` | DB 연결 상태 확인 |
| GET | `/version` | 앱 버전/모드 정보 |
| GET | `/` | 정적 HTML 메인 페이지 |
| GET | `/manifest.webmanifest` | PWA 매니페스트 |
| GET | `/sw.js` | Service Worker |

## Internal APIs (Worker ↔ Backend)

### Worker Analysis Handler
- **Interface**: `handlers/analysis.handle(message)`
- **Protocol**: HTTP POST to Backend `/cases/{case_id}/analyze`
- **Purpose**: Worker가 SQS 메시지를 받아 Backend의 분석 API를 호출

### Worker Transcription Handler (미구현)
- **Interface**: `handlers/transcription.handle(message)`
- **Protocol**: 계획 — S3 → Transcribe → Evidence 업데이트
- **Purpose**: 음성 파일 전사

## Data Models

### User
- id(UUID), email, phone_number, name, preferred_lang, nationality, provider, provider_id, status (cognito_sub는 Cognito 제거 이전의 nullable legacy column)

### Case
- id(UUID), user_id(FK), title, issue_type, status(draft/analyzing/completed), workplace_name, employer_name, work_start_date, work_end_date, agreed_hourly_wage(원), agreed_weekly_hours, issue_types(JSON), primary_language

### Evidence
- id(UUID), case_id(FK), category(contract/schedule/payment/chat/statement/other), file_type, file_name, s3_bucket, file_key, mime_type, file_size_bytes, ocr_status(pending/processing/done/failed), extraction_status, ocr_text, extracted_entities(JSON)

### CaseAnalysis
- id(UUID), case_id(FK), analysis_version, expected_wage_amount, actual_deposit_amount, difference_amount, deduction_summary(JSON), calculation_details(JSON), missing_documents(JSON), readiness_score, timeline_summary

### AnalysisResult
- id(UUID), case_id(FK), total_expected_wage, total_received_wage, suspected_unpaid, deduction_items(JSON), calculation_detail(JSON), timeline_summary, missing_evidences(JSON), pdf_ko_s3_key, pdf_native_s3_key

### TimelineEvent
- id(UUID), case_id(FK), event_type, title, description, description_translated, event_date, confidence(high/medium/low), source, source_evidence_id(FK)

### GpsLog
- id(UUID), case_id(FK), ts, lat, lng, is_mocked, is_delayed_upload, status(IN_WORKPLACE/OUTSIDE), chain_hash, device_id

### Workplace
- id(UUID), case_id(FK), center_lat, center_lng, radius_m(기본50)

### CommunityPost
- id(UUID), user_id(FK), anonymous_name, category, title, content, language_code, status, moderation_status, risk_level, counters(like/comment/saved/report/view)

### RagDocument + RagChunk
- document: id, title, source_org, language, document_type, chunks(relationship)
- chunk: id, document_id(FK), chunk_index, text, embedding(Vector 1024), keywords(JSON)

### ChatSession + ChatMessage
- session: id, user_id(FK), case_id(FK), language_code, status
- message: id, session_id(FK), role, message, intent, risk_level, used_rag, next_actions(JSON)
