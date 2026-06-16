# Implementation Plan: Speech-to-Text

## Overview

BADA에 오디오 파일 업로드 → Amazon Transcribe 비동기 전사 → 화자 분리 포맷팅 → 기존 엔티티 추출 파이프라인 합류를 구현한다. Provider 팩토리 패턴(기존 get_ocr, get_translator와 동일)을 따르며, Worker 전사 서비스 → Backend API 확장 → Frontend 확장 순서로 진행한다.

## Tasks

- [x] 1. Provider Layer — Transcriber ABC 및 데이터 타입 정의
  - [x] 1.1 Create `worker/providers/transcribe.py` with Transcriber ABC, data types, MockTranscriber, AmazonTranscriber, and `get_transcriber()` factory
    - Define `TranscriptionStatus`, `TranscriptionResult`, `SpeakerSegment` dataclasses
    - Implement `Transcriber` ABC with `start_job`, `get_job_status`, `get_result` abstract methods
    - Implement `MockTranscriber` returning fixed speaker-diarized placeholder text within 100ms
    - Implement `AmazonTranscriber` wrapping boto3 Transcribe client with diarization enabled (max 5 speakers)
    - Implement `get_transcriber()` factory checking `PROVIDER_MODE` (local → Mock, aws → Amazon)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 4.1_

  - [ ]* 1.2 Write property test for MockTranscriber performance (Property 7)
    - **Property 7: MockTranscriber performance constraint**
    - For any valid s3_uri and language_code, MockTranscriber returns within 100ms
    - **Validates: Requirements 6.4**

  - [ ]* 1.3 Write unit tests for provider factory
    - Test `get_transcriber()` returns `MockTranscriber` when PROVIDER_MODE="local"
    - Test `get_transcriber()` returns `AmazonTranscriber` when PROVIDER_MODE="aws"
    - Test `AmazonTranscriber.start_job` enables speaker diarization with MaxSpeakerLabels=5
    - _Requirements: 6.1, 6.2, 6.3, 4.1_

- [x] 2. Worker 전사 서비스 — process_transcription 및 format_diarized_text
  - [x] 2.1 Create `worker/services/transcription.py` with `process_transcription` and `format_diarized_text`
    - Implement `format_diarized_text(result: TranscriptionResult) -> str` formatting segments as "Speaker N: text\n"
    - Implement `process_transcription(evidence_id, s3_key, language_code)` orchestrating full flow:
      - Set Evidence.ocr_status → "processing"
      - Start transcription job with job naming convention `bada-{case_id[:8]}-{evidence_id[:8]}-{timestamp}`
      - Poll status every 5 seconds with 10-minute timeout
      - On success: format result, store in Evidence.ocr_text, set ocr_status="done"
      - On failure/timeout: set ocr_status="failed", log error reason
    - Default language_code to "ko-KR" when not provided
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.2, 4.2, 4.3_

  - [ ]* 2.2 Write property test for format_diarized_text (Property 5)
    - **Property 5: Speaker diarization formatting**
    - For any list of SpeakerSegment, output preserves order and content as "Speaker N: text" newline-separated
    - **Validates: Requirements 4.2**

  - [ ]* 2.3 Write property test for transcription result storage round-trip (Property 6)
    - **Property 6: Transcription result storage round-trip**
    - For any successful TranscriptionResult, stored ocr_text equals format_diarized_text output and ocr_status is "done"
    - **Validates: Requirements 2.3, 4.3**

  - [ ]* 2.4 Write unit tests for process_transcription
    - Test status transition: pending → processing → done
    - Test status transition: pending → processing → failed (on Transcribe failure)
    - Test 10-minute timeout triggers failed status with timeout reason
    - Test 5-second polling interval (mocked time.sleep)
    - Test default language_code is "ko-KR" when None provided
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.2_

- [x] 3. Checkpoint — Provider 및 Worker 서비스 검증
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Backend API 확장 — 오디오 업로드 및 검증
  - [x] 4.1 Extend `backend/app/routers/evidences.py` upload endpoint for audio support
    - Update `_guess_type()` to detect audio extensions (mp3, mp4, wav, flac, ogg, amr, webm) → return "audio"
    - Add `language_code: Optional[str] = Form(None)` parameter to `upload_file`
    - Validate file extension: reject non-audio unsupported extensions with HTTP 422
    - Validate file size: reject files > 200MB with HTTP 413
    - Validate language_code against supported set, reject invalid with HTTP 422 listing supported codes
    - On valid audio upload: create Evidence with file_type="audio", ocr_status="pending"
    - Publish SQS message with task="transcribe", evidence_id, case_id, s3_key, language_code
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.4_

  - [ ]* 4.2 Write property test for audio upload creates correct Evidence (Property 1)
    - **Property 1: Audio upload creates correct Evidence record**
    - For any valid audio extension and case_id, Evidence has file_type="audio", ocr_status="pending", correct file_key
    - **Validates: Requirements 1.1, 1.2**

  - [ ]* 4.3 Write property test for invalid audio extension rejection (Property 2)
    - **Property 2: Invalid audio extensions are rejected**
    - For any extension NOT in valid audio set, upload returns HTTP 422 with supported formats
    - **Validates: Requirements 1.3**

  - [ ]* 4.4 Write property tests for language_code validation (Properties 3, 4)
    - **Property 3: Valid language code acceptance and pass-through**
    - **Property 4: Invalid language code rejection**
    - For any valid code, API accepts it; for any invalid string, API returns 422 with supported list
    - **Validates: Requirements 3.1, 3.3, 3.4**

  - [ ]* 4.5 Write unit tests for upload endpoint edge cases
    - Test 200MB boundary (exactly 200MB passes, 200MB+1 byte fails with 413)
    - Test SQS message published with correct schema on audio upload
    - Test existing image/pdf upload behavior unchanged
    - _Requirements: 1.4, 1.5_

- [x] 5. Backend API 확장 — 전사 상태 조회
  - [x] 5.1 Extend `GET /cases/{case_id}/evidences/extract` response for audio evidence status
    - Include ocr_status for audio evidences in extract status response
    - Include ocr_text content when ocr_status is "done"
    - Include estimated progress indicator when available during "processing"
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. Checkpoint — Backend API 검증
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Frontend 확장 — 오디오 업로드 UI
  - [x] 7.1 Add audio upload card component to evidence upload UI
    - Add "audio" category option to evidence upload card
    - Accept audio file types (mp3, mp4, wav, flac, ogg, amr, webm) in file input
    - Add language selection dropdown with options: ko-KR(기본), vi-VN, en-US, th-TH, ja-JP, id-ID, km-KH, ne-NP
    - Submit audio file with category and language_code to `/upload` endpoint
    - _Requirements: 1.1, 3.1, 7.1_

  - [x] 7.2 Implement transcription status polling and result display
    - Poll `GET /extract` endpoint at regular intervals while ocr_status is "processing"
    - Display loading indicator with text "음성을 텍스트로 변환 중입니다" during processing
    - Display error message with retry option when ocr_status is "failed"
    - Display transcribed text when ocr_status is "done"
    - Visually distinguish speaker labels with alternating styles when diarization present
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 8. 기존 파이프라인 통합 — process_case에서 audio evidence 포함
  - [x] 8.1 Integrate audio evidence into existing entity extraction pipeline
    - Ensure Worker SQS consumer dispatches "transcribe" task to `process_transcription`
    - Verify `process_case` includes audio evidences with ocr_status="done" in analysis context
    - Ensure Evidence.ocr_text stores transcribed text in same field as image/pdf OCR results (no schema change needed)
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 8.2 Write integration test for end-to-end audio pipeline
    - Test: audio upload → SQS message → transcription → ocr_text stored → process_case includes it
    - Use MockTranscriber for fast local execution
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 9. Final Checkpoint — 전체 통합 검증
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirement clauses for traceability
- Property-based tests use the **hypothesis** library (Python) as specified in design
- Checkpoints ensure incremental validation at Provider, Backend, and Integration layers
- The design reuses `Evidence.ocr_text` and `ocr_status` fields — no DB migration needed
- Frontend tasks assume the existing React upload card pattern is extended (not recreated)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4"] },
    { "id": 3, "tasks": ["4.1", "5.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.4", "4.5"] },
    { "id": 5, "tasks": ["7.1", "8.1"] },
    { "id": 6, "tasks": ["7.2", "8.2"] }
  ]
}
```
