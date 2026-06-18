# 요구사항 문서 (한글 해설판)

## 소개

BADA 프로젝트에 음성 녹음 파일 업로드 + 텍스트 변환(Speech-to-Text) 기능을 추가한다.
외국인 노동자가 사업주와의 대화를 녹음한 음성 파일을 증거로 올리면,
Amazon Transcribe가 텍스트로 전사하고 결과를 Evidence.ocr_text에 저장한다.
이후 기존 OCR 엔티티 추출 파이프라인에 자연스럽게 합류한다.

## 용어 설명

| 용어 | 뜻 |
|------|-----|
| Transcription_Service | Amazon Transcribe를 감싸는 프로바이더 모듈. Mock/AWS 분기 |
| Transcription_Job | Amazon Transcribe에 제출하는 비동기 전사 작업 단위 |
| Evidence | 사건에 첨부된 증거 레코드 (file_type, ocr_status, ocr_text) |
| Speaker_Diarization | 화자 분리. 녹음에서 누가 말했는지 구분 |
| Audio_File | 지원 음성 형식: mp3, mp4, wav, flac, ogg, amr, webm |
| Polling | 프론트엔드가 전사 진행 상태를 주기적으로 조회하는 방식 |

---

## 요구사항 목록

### 요구사항 1: 오디오 파일 업로드

**사용자 스토리:** 외국인 노동자로서, 음성 녹음 파일을 증거로 업로드하고 싶다. 사업주와의 대화 녹음을 임금체불 증거로 쓰기 위해서.

**합격 기준:**

1. mp3/mp4/wav/flac/ogg/amr/webm 확장자 파일 업로드 시 → S3에 `cases/{case_id}/{파일명}`으로 저장
2. 오디오 업로드 시 → Evidence 레코드 생성 (file_type="audio", ocr_status="pending")
3. 지원하지 않는 확장자 → HTTP 422 + 지원 형식 안내
4. 최대 파일 크기 200MB 제한
5. 200MB 초과 → HTTP 413 에러

---

### 요구사항 2: 비동기 전사 처리

**사용자 스토리:** 외국인 노동자로서, 업로드한 음성이 자동으로 텍스트로 변환되기를 원한다.

**합격 기준:**

1. Evidence가 "pending"이면 → Worker가 Transcribe 잡 제출
2. 잡 제출 시 → ocr_status를 "processing"으로 변경
3. 잡 성공 시 → 전사 텍스트를 ocr_text에 저장, ocr_status="done"
4. 잡 실패 시 → ocr_status="failed", 에러 사유 로깅
5. 5초 간격으로 폴링하며 완료/실패를 대기
6. 10분 초과 시 → "failed" + timeout 사유

---

### 요구사항 3: 언어 지정

**사용자 스토리:** 녹음 언어를 지정해서 전사 정확도를 높이고 싶다.

**합격 기준:**

1. 업로드 시 선택적 `language_code` 파라미터 지원 (ko-KR, vi-VN, en-US, th-TH, ja-JP, id-ID, km-KH, ne-NP)
2. 미지정 시 → 기본값 ko-KR
3. 지정 시 → Amazon Transcribe에 그대로 전달
4. 지원하지 않는 코드 → HTTP 422 + 지원 목록 안내

---

### 요구사항 4: 화자 분리

**사용자 스토리:** 녹음에서 사업주와 노동자의 발화가 구분되기를 원한다.

**합격 기준:**

1. 모든 전사 잡에 화자 분리 활성화 (최대 5명)
2. 화자 분리 결과 있을 시 → "Speaker 0:", "Speaker 1:" 형태로 포맷
3. 포맷된 텍스트를 Evidence.ocr_text에 저장

---

### 요구사항 5: 전사 상태 조회

**사용자 스토리:** 프론트엔드에서 전사 진행 상태를 조회해서 사용자에게 보여주고 싶다.

**합격 기준:**

1. GET /extract 엔드포인트에서 → 오디오 Evidence의 ocr_status 반환
2. "processing" 상태일 때 → 진행 표시기 포함 (가능한 경우)
3. "done" 상태일 때 → ocr_text 내용 포함

---

### 요구사항 6: 프로바이더 모드 분기

**사용자 스토리:** 개발자로서, PROVIDER_MODE로 Mock/AWS를 전환해서 로컬에서도 테스트하고 싶다.

**합격 기준:**

1. PROVIDER_MODE=local → MockTranscriber (AWS 호출 없이 고정 텍스트 반환)
2. PROVIDER_MODE=aws → AmazonTranscriber (실제 Transcribe 호출)
3. 기존 프로바이더 팩토리 패턴 동일하게 따름 (get_ocr, get_translator처럼)
4. MockTranscriber는 100ms 이내 응답

---

### 요구사항 7: 전사 결과 표시

**사용자 스토리:** 전사 결과를 화면에서 텍스트로 확인하고 싶다.

**합격 기준:**

1. ocr_status="done" → 텍스트 표시
2. ocr_status="processing" → "음성을 텍스트로 변환 중입니다" 로딩 표시
3. ocr_status="failed" → 에러 메시지 + 재시도 버튼
4. 화자 라벨이 있으면 → 화자별로 시각적 구분 (교대 스타일)

---

### 요구사항 8: 기존 파이프라인 통합

**사용자 스토리:** 전사 결과가 기존 OCR 파이프라인과 동일하게 분석에 포함되어야 한다.

**합격 기준:**

1. ocr_status="done"인 오디오 Evidence → 기존 엔티티 추출 파이프라인에서 동일하게 처리
2. Evidence.ocr_text 필드를 이미지/PDF OCR과 동일하게 사용 (별도 컬럼 없음)
3. process_case 호출 시 → 오디오 Evidence도 분석 컨텍스트에 포함
