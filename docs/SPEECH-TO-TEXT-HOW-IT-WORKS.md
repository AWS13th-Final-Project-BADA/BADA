# BADA 음성 인식(Speech-to-Text) — 내부 동작 원리

> 한 문장 원칙: **오디오 업로드 → Amazon Transcribe 전사 → 화자 분리 → Claude 보정 → 기존 파이프라인 합류.**
> 전사 결과는 Evidence.ocr_text에 저장되어 기존 OCR 결과와 동일하게 분석에 사용된다.

---

## 0. 큰 그림

```
[사용자] 오디오 파일 업로드 (mp3/m4a/wav/...)
   │  POST /cases/{id}/evidences/upload (category=audio)
   ▼
[backend/routers/evidences]
   ├─ S3에 저장 (cases/{case_id}/{filename})
   ├─ Evidence 생성 (file_type=audio, ocr_status=processing)
   └─ 백그라운드 전사 시작
        │
        ▼
[Amazon Transcribe]
   ├─ 채널 식별 시도 (스테레오 = 전화 통화)
   │   └─ 실패(모노) → 화자 분리(diarization) 폴백
   ├─ Custom Vocabulary 적용 (bada-labor-vocab, 한국어)
   └─ 5초 간격 폴링 (최대 10분)
        │
        ▼
[worker/services/transcription]
   ├─ 결과 파싱 (채널별 or 화자별 세그먼트)
   ├─ "Speaker 0: text\nSpeaker 1: text" 포맷팅
   ├─ Claude 후처리 (오인식 교정, 도메인 용어 보정)
   └─ Evidence.ocr_text에 저장, ocr_status=done
        │
        ▼
[기존 파이프라인] process_case에서 ocr_text 동일하게 사용
```

---

## 1. 지원 형식

| 확장자 | 비고 |
|--------|------|
| mp3 | 일반 녹음 |
| mp4 / m4a | iOS 음성 메모 (AAC) |
| wav | PCM, 전화 통화 녹음 |
| flac | 무손실 |
| ogg | 안드로이드 녹음 |
| amr | 피처폰 녹음 |
| webm | 브라우저 녹음 |

- 최대 파일 크기: **200MB**
- 다중 파일 업로드 지원 (프론트에서 순차 전송)

---

## 2. 파일 구조

```
worker/
├─ providers/
│  └─ transcribe.py        # Transcriber ABC, MockTranscriber, AmazonTranscriber, get_transcriber()
├─ services/
│  └─ transcription.py     # process_transcription(), format_diarized_text(), refine_transcript()
└─ config.py               # PROVIDER_MODE, TRANSCRIBE_MODE

backend/app/routers/
└─ evidences.py            # /upload 엔드포인트 (오디오 분기)
```

---

## 3. 전화 통화 최적화

전화 통화 녹음(BADA의 주 사용 사례)에 맞춘 3단계 최적화:

### 3-1. 채널 식별 우선 (ChannelIdentification)
- 스테레오 파일(발신/수신 각 채널) → 물리적으로 화자 분리
- 모노 파일 → 자동 폴백하여 AI 화자 분리(diarization, 최대 5명)

### 3-2. Custom Vocabulary (`bada-labor-vocab`)
- 노동 도메인 단어 35개 등록 (월급, 시급, 공제, 기숙사비, 고용노동부 등)
- **자동 생성**: 첫 전사 시 Vocabulary가 없으면 코드가 자동으로 만듦
- READY 상태일 때만 적용, 아직 PENDING이면 Vocabulary 없이 진행
- 한국어(ko-KR)일 때만 적용

### 3-3. Claude 후처리 (refine_transcript)
- Transcribe 원문을 Bedrock Claude에 보내 교정
- 교정 대상: 음성인식 오타, 도메인 용어, 빠진 조사/어미
- **절대 없는 내용을 추가하지 않음** (프롬프트에 명시)
- 실패 시 원문 유지 (graceful degradation)
- `PROVIDER_MODE=local`이면 보정 건너뜀

---

## 4. 결과 파싱

### 채널 식별 결과 (스테레오)
```
채널 0의 items → Speaker 0
채널 1의 items → Speaker 1
→ 시간순 정렬하여 대화 흐름 재구성
→ 2초 이상 gap이면 별도 세그먼트로 분리
```

### 화자 분리 결과 (모노 폴백)
```
speaker_labels.segments → item별 화자 매핑
→ 연속 동일 화자 발화를 하나로 결합
→ "Speaker 0: text\nSpeaker 1: text" 포맷
```

### 최종 저장 형식 (Evidence.ocr_text)
```
Speaker 0: 안녕하세요, 이번 달 급여가 아직 입금되지 않았습니다.
Speaker 1: 네, 확인해보겠습니다. 잠시만 기다려주세요.
Speaker 0: 지난달에도 같은 문제가 있었는데, 이번에도 늦어지는 건가요?
```

---

## 5. 지원 언어 코드 (Transcribe)

| BADA 언어 | Transcribe 코드 | 비고 |
|-----------|----------------|------|
| ko | ko-KR | 기본값 |
| vi | vi-VN | |
| en | en-US | |
| th | th-TH | |
| ja | ja-JP | |
| id | id-ID | |
| km | km-KH | 지원 제한적 |
| ne | ne-NP | 지원 제한적 |

- 업로드 시 `language_code` 파라미터로 지정 (미지정 시 ko-KR)
- 지원하지 않는 코드 → HTTP 422

---

## 6. 기존 파이프라인 통합

- `Evidence.ocr_text`에 전사 텍스트 저장 → 이미지/PDF OCR과 **동일 필드**
- `process_case` 실행 시 오디오 Evidence도 분석 컨텍스트에 포함
- DB 스키마 변경 없음 — `file_type="audio"` 값만 새로 사용
- 카테고리는 `audio` (프론트 업로드 카드에서 선택)

---

## 7. 에러 처리

| 실패 유형 | 처리 |
|-----------|------|
| Transcribe 잡 실패 | ocr_status="failed", 사유 로깅 |
| 10분 타임아웃 | ocr_status="failed", reason="timeout" |
| S3 접근 오류 | ocr_status="failed" |
| 빈 전사 결과 (무음) | ocr_text="", ocr_status="done" (유효) |
| Claude 보정 실패 | Transcribe 원문 유지 |
| Vocabulary 생성 실패 | Vocabulary 없이 전사 진행 |

- 자동 재시도 없음 (사용자가 UI에서 "다시 시도" 클릭)

---

## 8. 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `PROVIDER_MODE` | local | OCR/LLM 등 공통 provider 모드 |
| `TRANSCRIBE_MODE` | `PROVIDER_MODE` 상속 | local=MockTranscriber, aws=AmazonTranscriber |
| `AWS_REGION` | ap-northeast-2 | Transcribe 리전 |
| `S3_BUCKET` | | 오디오 파일 저장 버킷 (S3 모드 필수) |

AWS dev 환경은 다른 provider의 비용과 동작에 영향을 주지 않도록 다음처럼 사용한다.

```text
PROVIDER_MODE=local
TRANSCRIBE_MODE=aws
TRANSCRIPTION_DISPATCH_MODE=inline
```

---

## 9. 프론트엔드

- 업로드 카드: 🎤 "음성 녹음" (accept: audio/*, .m4a 포함)
- **다중 파일 선택** 지원 (순차 업로드, "2/5 업로드 중..." 표시)
- 전사 상태 폴링:
  - `processing` → "⏳ 음성을 텍스트로 변환 중입니다"
  - `done` → 화자별 텍스트 표시 (Speaker 0/1 구분 스타일)
  - `failed` → 에러 메시지 + "다시 시도" 버튼

---

## 10. 테스트

```bash
cd worker && python -m pytest tests/ -v -k "transcri"
```

- MockTranscriber: 100ms 이내 고정 응답 → 로컬 E2E 동작
- 실제 전사: `TRANSCRIBE_MODE=aws` + S3 버킷 설정 필요
- AWS 실측 결과: S3 업로드 ✅, Transcribe 잡 생성 ✅, 결과 가져오기 ✅

---

## 11. 알려진 제한

- 8kHz 모노(전화 통화) → 채널 식별 불가, 화자 분리 정확도 제한적
- 배경 소음 많으면 인식률 하락
- Custom Vocabulary는 한국어(ko-KR)에만 적용
- 음악/비대화 오디오는 인식 불가 (대화 녹음용)
