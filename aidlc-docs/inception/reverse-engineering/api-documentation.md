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
| POST | `/chat/messages` | 챗봇 메시지 전송 및 응답 수신 (case_id는 body, UUID 문자열; 미지정 시 일반 상담) |

### Auth (`/auth`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/{provider}/login` | 소셜 로그인 시작 (kakao, google, naver) |
| GET | `/auth/{provider}/callback` | 소셜 로그인 콜백 (code 교환 → JWT 발급) |
| POST | `/auth/kakao/link-code` | 카카오톡 연동 코드 발급 |
| GET | `/auth/me` | 현재 로그인 사용자 정보 |
| POST | `/auth/logout` | 로그아웃 (클라이언트 토큰 삭제) |

> 인증 토큰은 외부 IdP 없이 백엔드가 자체 발급하는 **HS256 JWT**(기본 7일 만료)다. 모바일 클라이언트는 API가 401을 반환하면 저장 토큰을 삭제하고 로그인 화면으로 이동한다(자동 로그아웃). Cognito는 앱 인증 경로에서 제거되어 소셜 OAuth(Google/Kakao/Naver) 직접 구현으로 단일화됨.

### Kakao Skill (`/kakao`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/kakao/skill` | 카카오톡 스킬 서버 메시지 수신 (대화·증거·GPS·분석 라우팅) |

### Community (`/community`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/community/posts` | 게시글 피드 (카테고리/언어 필터) |
| POST | `/community/posts` | 게시글 작성 |
| GET | `/community/posts/{post_id}` | 게시글 상세 |
| PATCH | `/community/posts/{post_id}` | 게시글 수정 |
| DELETE | `/community/posts/{post_id}` | 게시글 삭제 |
| GET | `/community/posts/{post_id}/comments` | 댓글 목록 |
| POST | `/community/posts/{post_id}/comments` | 댓글 작성 |
| GET | `/community/comments/{comment_id}` | 댓글 상세 |
| PATCH | `/community/comments/{comment_id}` | 댓글 수정 |
| DELETE | `/community/comments/{comment_id}` | 댓글 삭제 |
| POST | `/community/reactions` | 좋아요/저장 토글 |
| POST | `/community/translate` | 게시글/댓글 번역 요청 |
| POST | `/community/reports` | 신고 접수 |
| GET | `/community/reports` | 신고 목록 (관리자) |
| PATCH | `/community/reports/{report_id}` | 신고 처리 |
| POST | `/community/safety-check` | 게시글 안전성 사전 검사 |
| GET | `/community/boards` | 게시판 카테고리 목록 |

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
- id(UUID), cognito_sub, email, phone_number, name, preferred_lang, nationality, provider, provider_id, status

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
