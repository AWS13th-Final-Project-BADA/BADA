# Requirements Document

## Introduction

BADA 프로젝트에 음성 녹음 파일(오디오) 업로드 및 텍스트 변환(Speech-to-Text) 기능을 추가한다. 외국인 노동자가 사업주와의 대화를 녹음한 음성 파일을 증거로 업로드하면, Amazon Transcribe를 통해 텍스트로 전사(transcription)하고 결과를 Evidence.ocr_text 필드에 저장한다. 전사 결과는 프론트엔드에서 텍스트로 표시되며, 이후 기존 엔티티 추출 파이프라인에 자연스럽게 합류한다.

## Glossary

- **Transcription_Service**: Amazon Transcribe를 래핑하는 worker/providers 내 프로바이더 모듈. PROVIDER_MODE에 따라 AmazonTranscriber 또는 MockTranscriber를 반환한다.
- **Transcription_Job**: Amazon Transcribe에 제출되는 비동기 전사 작업 단위. S3 오디오 파일을 입력받아 텍스트 결과를 생성한다.
- **Evidence**: 사건(Case)에 첨부된 증거 레코드. file_type, ocr_status, ocr_text 필드를 포함한다.
- **Backend_API**: FastAPI 기반 백엔드 서버. 증거 업로드 엔드포인트와 전사 상태 조회 엔드포인트를 제공한다.
- **Worker**: SQS 메시지를 소비하여 비동기 처리(OCR, 전사 등)를 수행하는 컨테이너.
- **Speaker_Diarization**: 화자 분리 기능. 녹음 내 각 발화 구간을 화자별로 분리하여 표시한다.
- **Audio_File**: 업로드 가능한 음성 파일. 지원 형식은 mp3, mp4, wav, flac, ogg, amr, webm이다.
- **Polling**: 프론트엔드가 전사 진행 상태를 주기적으로 조회하는 방식.

## Requirements

### Requirement 1: 오디오 파일 업로드

**User Story:** As a 외국인 노동자, I want 음성 녹음 파일을 증거로 업로드할 수 있기를, so that 사업주와의 대화 녹음을 임금체불 증거로 활용할 수 있다.

#### Acceptance Criteria

1. WHEN a user uploads a file with extension mp3, mp4, wav, flac, ogg, amr, or webm, THE Backend_API SHALL accept the file and store it in S3 with the key pattern `cases/{case_id}/{file_name}`.
2. WHEN a user uploads an Audio_File, THE Backend_API SHALL create an Evidence record with file_type set to "audio" and ocr_status set to "pending".
3. IF a user uploads a file with an unsupported audio extension, THEN THE Backend_API SHALL return HTTP 422 with a descriptive error message indicating the supported formats.
4. THE Backend_API SHALL enforce a maximum file size of 200MB for Audio_File uploads.
5. IF a user uploads an Audio_File exceeding 200MB, THEN THE Backend_API SHALL return HTTP 413 with a descriptive error message.

### Requirement 2: 비동기 전사 처리

**User Story:** As a 외국인 노동자, I want 업로드한 음성 파일이 자동으로 텍스트로 변환되기를, so that 녹음 내용을 증거 텍스트로 활용할 수 있다.

#### Acceptance Criteria

1. WHEN an Audio_File Evidence record is created with ocr_status "pending", THE Worker SHALL submit a Transcription_Job to the Transcription_Service.
2. WHEN a Transcription_Job is submitted, THE Worker SHALL set the Evidence ocr_status to "processing".
3. WHEN the Transcription_Job completes successfully, THE Worker SHALL store the transcribed text in the Evidence ocr_text field and set ocr_status to "done".
4. IF the Transcription_Job fails, THEN THE Worker SHALL set the Evidence ocr_status to "failed" and log the error reason.
5. THE Worker SHALL poll the Transcription_Job status at intervals of 5 seconds until completion or failure.
6. IF the Transcription_Job does not complete within 10 minutes, THEN THE Worker SHALL mark the Evidence ocr_status as "failed" with a timeout reason.

### Requirement 3: 언어 지정

**User Story:** As a 외국인 노동자, I want 녹음 언어를 지정할 수 있기를, so that 전사 정확도가 높아진다.

#### Acceptance Criteria

1. WHEN a user uploads an Audio_File, THE Backend_API SHALL accept an optional language_code parameter with values ko-KR, vi-VN, en-US, th-TH, ja-JP, id-ID, km-KH, or ne-NP.
2. IF a language_code is not provided, THEN THE Transcription_Service SHALL default to ko-KR.
3. WHEN a language_code is provided, THE Transcription_Service SHALL pass the language_code to Amazon Transcribe as the LanguageCode parameter.
4. IF an unsupported language_code is provided, THEN THE Backend_API SHALL return HTTP 422 with the list of supported language codes.

### Requirement 4: 화자 분리

**User Story:** As a 외국인 노동자, I want 녹음에서 사업주와 노동자의 발화가 구분되기를, so that 누가 어떤 말을 했는지 명확히 할 수 있다.

#### Acceptance Criteria

1. THE Transcription_Service SHALL enable Speaker_Diarization with a maximum of 5 speakers for every Transcription_Job.
2. WHEN Speaker_Diarization results are available, THE Worker SHALL format the transcribed text with speaker labels (e.g., "Speaker 0:", "Speaker 1:") prefixed to each segment.
3. WHEN Speaker_Diarization results are available, THE Worker SHALL store the speaker-labeled text in the Evidence ocr_text field.

### Requirement 5: 전사 상태 조회

**User Story:** As a 프론트엔드 클라이언트, I want 전사 진행 상태를 조회할 수 있기를, so that 사용자에게 처리 진행 상황을 표시할 수 있다.

#### Acceptance Criteria

1. WHEN a client sends a GET request to the evidence extract status endpoint, THE Backend_API SHALL return the current ocr_status of the Audio_File Evidence.
2. WHILE an Audio_File Evidence has ocr_status "processing", THE Backend_API SHALL include an estimated progress indicator in the response when available.
3. WHEN an Audio_File Evidence has ocr_status "done", THE Backend_API SHALL include the ocr_text content in the response.

### Requirement 6: 프로바이더 모드 분기

**User Story:** As a 개발자, I want PROVIDER_MODE에 따라 Mock과 실제 Transcribe 구현이 전환되기를, so that AWS 없이도 로컬 개발과 테스트가 가능하다.

#### Acceptance Criteria

1. WHILE PROVIDER_MODE is set to "local", THE Transcription_Service SHALL return a MockTranscriber that produces a fixed placeholder text without calling AWS.
2. WHILE PROVIDER_MODE is set to "aws", THE Transcription_Service SHALL return an AmazonTranscriber that submits jobs to Amazon Transcribe.
3. THE Transcription_Service SHALL follow the same provider factory pattern used by existing providers (get_ocr, get_translator, get_llm).
4. THE MockTranscriber SHALL return a response within 100 milliseconds to enable fast local testing.

### Requirement 7: 전사 결과 표시

**User Story:** As a 외국인 노동자, I want 전사 결과를 화면에서 텍스트로 확인할 수 있기를, so that 녹음 내용이 올바르게 인식되었는지 확인할 수 있다.

#### Acceptance Criteria

1. WHEN an Audio_File Evidence has ocr_status "done", THE Frontend SHALL display the ocr_text content in the evidence detail view.
2. WHILE an Audio_File Evidence has ocr_status "processing", THE Frontend SHALL display a loading indicator with the text "음성을 텍스트로 변환 중입니다".
3. IF an Audio_File Evidence has ocr_status "failed", THEN THE Frontend SHALL display an error message with a retry option.
4. WHEN Speaker_Diarization labels are present in ocr_text, THE Frontend SHALL visually distinguish different speakers using alternating styles.

### Requirement 8: 기존 파이프라인 통합

**User Story:** As a 시스템, I want 전사 결과가 기존 OCR 엔티티 추출 파이프라인에 합류하기를, so that 음성 증거도 동일한 분석 흐름을 거친다.

#### Acceptance Criteria

1. WHEN an Audio_File Evidence reaches ocr_status "done", THE Worker SHALL make the ocr_text available to the entity extraction pipeline in the same format as image/pdf OCR results.
2. THE Worker SHALL store the transcribed text in Evidence.ocr_text using the same field used by image and PDF OCR results.
3. WHEN process_case is invoked, THE Worker SHALL include Audio_File evidences with ocr_status "done" in the analysis context alongside other evidence types.
