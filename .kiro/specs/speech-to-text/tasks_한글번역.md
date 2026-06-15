# 구현 계획 (한글 해설판)

## 개요

BADA에 오디오 업로드 → Amazon Transcribe 비동기 전사 → 화자 분리 포맷팅 → 기존 파이프라인 합류를 구현한다.
기존 get_ocr, get_translator와 동일한 Provider 팩토리 패턴을 따른다.

---

## 작업 목록

### ✅ 작업 1: Provider Layer (Transcriber 인터페이스)

#### ✅ 1.1 `worker/providers/transcribe.py` 생성
**뭘 만드나:**
- `TranscriptionStatus`, `TranscriptionResult`, `SpeakerSegment` 데이터 클래스
- `Transcriber` ABC — `start_job`, `get_job_status`, `get_result` 추상 메서드
- `MockTranscriber` — 고정 화자 분리 텍스트 즉시 반환 (100ms 이내)
- `AmazonTranscriber` — boto3 Transcribe 클라이언트, 화자 분리 활성화 (최대 5명)
- `get_transcriber()` 팩토리 — PROVIDER_MODE에 따라 Mock/Amazon 분기

**관련 요구사항:** 6.1~6.4, 4.1

---

### ✅ 작업 2: Worker 전사 서비스

#### ✅ 2.1 `worker/services/transcription.py` 생성
**뭘 만드나:**
- `format_diarized_text(result)` — 화자별 세그먼트를 "Speaker N: text\n" 형식으로 결합
- `process_transcription(s3_uri, language_code, job_name)` — 전체 흐름 오케스트레이션:
  - Transcribe 잡 시작
  - 5초 간격 폴링 (최대 10분)
  - 성공 시 포맷팅된 텍스트 반환
  - 실패/타임아웃 시 에러 사유 반환
- language_code 미지정 시 기본값 "ko-KR"

**관련 요구사항:** 2.1~2.6, 3.2, 4.2, 4.3

---

### ✅ 작업 3: 체크포인트 — Provider + Worker 서비스 검증

---

### ✅ 작업 4: Backend API 확장 (오디오 업로드)

#### ✅ 4.1 `backend/app/routers/evidences.py` 업로드 엔드포인트 확장
**뭘 바꾸나:**
- `_guess_type()` — 오디오 확장자 감지 → file_type="audio" 반환
- `language_code` 파라미터 추가 (Form, optional)
- 파일 확장자 검증: 지원하지 않으면 HTTP 422
- 파일 크기 검증: 200MB 초과 시 HTTP 413
- language_code 검증: 지원 안 하면 HTTP 422 + 지원 목록
- 유효한 오디오 업로드 → Evidence 생성 + 백그라운드 전사 시작 (또는 SQS 메시지)

**관련 요구사항:** 1.1~1.5, 3.1, 3.4

---

### ✅ 작업 5: Backend API 확장 (전사 상태 조회)

#### ✅ 5.1 `GET /extract` 응답에 오디오 evidence 포함
**뭘 바꾸나:**
- `ocr_service.py`의 `_eligible()` 함수에 "audio" 추가
- 기존 폴링 메커니즘으로 오디오 전사 상태도 조회 가능

**관련 요구사항:** 5.1~5.3

---

### ✅ 작업 6: 체크포인트 — Backend API 검증

---

### ✅ 작업 7: Frontend 확장 (오디오 업로드 UI)

#### ✅ 7.1 업로드 카드에 "음성 녹음" 항목 추가
**뭘 바꾸나:**
- ROWS 배열에 `{cat:"audio", icon:마이크, tk:"up_audio", sk:"up_audio_desc"}` 추가
- 오디오 카드의 file input은 `accept="audio/*"` 설정
- i18n.js에 8개 언어로 up_audio 키 추가

#### ✅ 7.2 전사 상태 폴링 + 결과 표시
**뭘 바꾸나:**
- "processing" 상태 → "음성을 텍스트로 변환 중입니다" 표시
- "failed" 상태 → 에러 + 재시도 버튼
- "done" 상태 → 화자별 텍스트 표시 (Speaker 0/1 구분 스타일)

**관련 요구사항:** 7.1~7.4

---

### ✅ 작업 8: 기존 파이프라인 통합

#### ✅ 8.1 process_case에서 audio evidence 포함
**뭘 확인하나:**
- Evidence.ocr_text에 전사 텍스트 저장 (이미지/PDF OCR과 동일 필드)
- process_case 실행 시 오디오 evidence도 분석 컨텍스트에 포함
- DB 스키마 변경 없음 — file_type="audio" 값만 새로 사용

**관련 요구사항:** 8.1~8.3

---

### ✅ 작업 9: 최종 체크포인트 — 전체 통합 검증

---

## 참고사항

- `*` 표시 작업은 **선택사항** (property-based test)
- 기존 OCR 모듈은 건드리지 않음 — 완전히 독립된 새 모듈
- DB 마이그레이션 없음 — ocr_text, ocr_status 필드 재사용
- MockTranscriber로 로컬 테스트 가능 (AWS 없이도 전체 흐름 동작)
- 실제 음성 인식은 PROVIDER_MODE=aws + S3 버킷 설정 필요

---

## 작업 의존성 그래프 (순서)

```
Wave 0: [1.1] Transcriber 프로바이더 생성
         ↓
Wave 1: [2.1] Worker 전사 서비스 구현
         ↓
Wave 2: (선택) Property/Unit 테스트
         ↓
Wave 3: [4.1] Backend 업로드 확장, [5.1] 상태 조회 확장 — 병렬
         ↓
Wave 4: (선택) API 테스트
         ↓
Wave 5: [7.1] 프론트엔드 카드, [8.1] 파이프라인 통합 — 병렬
         ↓
Wave 6: [7.2] 결과 표시, (선택) 통합 테스트
```

---

## AWS 테스트 결과 (실측)

- S3 업로드 ✅ — 파일 정상 저장 확인
- Transcribe 잡 생성 ✅ — COMPLETED 상태 확인
- 결과 가져오기 ✅ — TranscriptFileUri 정상 존재
- 텍스트 인식 ⚠️ — 음악 파일은 가사를 인식하지 못함 (대화 녹음 파일로 재테스트 필요)
- 파이프라인 흐름 ✅ — Mock으로 전체 E2E 동작 확인
