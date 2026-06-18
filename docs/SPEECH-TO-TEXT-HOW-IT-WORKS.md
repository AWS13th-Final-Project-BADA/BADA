# BADA 음성 인식(Speech-to-Text) — 내부 동작 원리

> 한 문장 원칙: **오디오 업로드 → Amazon Transcribe 텍스트 추출 → Bedrock Claude 화자 분리+교정 → 기존 파이프라인 합류.**
> Transcribe는 텍스트만 뽑고, 화자 구분과 교정은 Claude가 담당한다.

---

## 0. 큰 그림

```
[사용자] 오디오 파일 업로드 (mp3/m4a/wav/...)
   │  POST /cases/{id}/evidences/upload (category=audio)
   ▼
[backend/routers/evidences]
   ├─ S3에 저장 (cases/{날짜}_{사업장}_{case_id[:8]}/{filename})
   ├─ Evidence 생성 (file_type=audio, ocr_status=processing)
   └─ 전사 디스패치 (inline 또는 SQS)
        │
        ▼
[Amazon Transcribe]
   ├─ 채널 식별 시도 (스테레오 → 물리적 화자 분리)
   │   └─ 모노 → 화자 분리(diarization) 폴백
   ├─ Custom Vocabulary 적용 (bada-labor-vocab, 한국어)
   └─ 5초 간격 폴링 (최대 10분)
        │
        ▼
[Bedrock Claude 후처리] ★ 핵심 단계
   ├─ 텍스트 교정 (오인식, 도메인 용어, 조사/어미 복원)
   └─ 화자 분리 (대화 맥락 기반 → "사업주:" / "노동자:" 라벨링)
        │
        ▼
[Evidence.ocr_text 저장] → 기존 파이프라인 합류
```

핵심 설계 결정: **Transcribe의 한국어 화자 분리는 모노 전화 통화에서 부정확** (전부 Speaker 0으로 나옴).
따라서 Transcribe는 텍스트 추출 엔진으로만 사용하고, **화자 구분은 Claude가 대화 맥락으로 판별**한다.

---

## 1. 지원 형식

| 확장자 | 비고 |
|--------|------|
| mp3 | 일반 녹음 |
| mp4 / m4a | iOS 음성 메모 (AAC) ★ |
| wav | PCM, 전화 통화 녹음 |
| flac | 무손실 |
| ogg | 안드로이드 녹음 |
| amr | 피처폰 녹음 |
| webm | 브라우저 녹음 |

- 최대 파일 크기: **200MB**
- **다중 파일 업로드** 지원 (프론트에서 순차 전송, 진행 카운터 표시)

---

## 2. 파일 구조

```
worker/
├─ providers/
│  └─ transcribe.py        # Transcriber ABC, MockTranscriber, AmazonTranscriber
│                           # Custom Vocabulary 자동 생성, 채널 식별/diarization 폴백
├─ services/
│  └─ transcription.py     # process_transcription(), format_diarized_text(), refine_transcript()
│                           # Claude 후처리 프롬프트 (화자 분리 + 텍스트 교정)
└─ config.py               # PROVIDER_MODE, TRANSCRIBE_MODE

backend/app/routers/
└─ evidences.py            # /upload (오디오 분기), _run_local_transcription()
                           # TRANSCRIPTION_DISPATCH_MODE: inline | sqs
```

---

## 3. 전사 파이프라인 상세

### 3-1. Transcribe 설정

**채널 식별 우선 전략:**
- 스테레오 파일 → `ChannelIdentification=True` (물리적 화자 분리, 가장 정확)
- 모노 파일 → 채널 식별 실패 시 자동 폴백: `ShowSpeakerLabels=True, MaxSpeakerLabels=5`

**Custom Vocabulary (`bada-labor-vocab`):**
- 노동 도메인 단어 35개 등록:
  - 임금: 월급, 시급, 공제, 기숙사비, 숙소비, 식비, 수당, 주휴수당
  - 근로: 야근, 잔업, 연장근로, 야간근로, 근무표, 출퇴근
  - 법률: 고용노동부, 노동청, 근로감독관, 진정서, 부당해고, 권고사직
  - 보험: 국민연금, 건강보험, 고용보험, 산재보험
  - 호칭: 사업주, 사장님, 대표님, 공장장
- **자동 생성**: `AmazonTranscriber` 초기화 시 Vocabulary 없으면 자동 create
- READY 상태일 때만 적용, PENDING이면 Vocabulary 없이 진행
- 한국어(ko-KR)일 때만 적용

### 3-2. Claude 후처리 (refine_transcript) ★

Transcribe 원문을 Bedrock Claude에 보내 **두 가지를 동시에** 처리:

**화자 분리 (핵심):**
- 대화 맥락으로 "사업주" vs "노동자" 판별
- 사업주 패턴: 지시, "처리하겠다", "확인하겠다", 급여를 주는 쪽
- 노동자 패턴: 요청, "안 들어왔다", "언제 주나", 급여를 받는 쪽
- 구분 불가 시 "화자미상:" 표기

**텍스트 교정:**
- 음성인식 오타 교정 (문맥 기반)
- 도메인 용어 보정
- 빠진 조사/어미 복원
- **없는 내용 절대 추가 금지**

**출력 형식:**
```
사업주: 이번 달 급여는 다음 주에 처리하겠습니다.
노동자: 지난달에도 같은 말씀하셨는데, 정확히 언제 입금되나요?
사업주: 금요일까지는 확인해보겠습니다.
```

**Graceful degradation:**
- Claude 실패 시 → Transcribe 원문 그대로 유지 (Speaker 0: ... 형태)
- 보정 결과가 원문의 50% 미만이면 → 원문 유지 (안전장치)
- `PROVIDER_MODE=local`이면 → 보정 건너뜀 (Mock 모드)

### 3-3. 왜 이 구조인가

| 역할 | Transcribe | Claude |
|------|-----------|--------|
| 텍스트 추출 | ✅ 주 담당 | 보조 (교정) |
| 화자 분리 | ❌ 모노에서 부정확 | ✅ 맥락 기반 판별 |
| 비용 | 분당 과금 | 토큰 과금 (~$0.01/건) |
| 속도 | 수초~수십초 | 1~2초 추가 |

---

## 4. 디스패치 모드 (TRANSCRIPTION_DISPATCH_MODE)

| 모드 | 설명 | 사용 환경 |
|------|------|-----------|
| `inline` (기본) | Backend 프로세스 안에서 직접 전사 (백그라운드 스레드) | ECS 단일 Task, 로컬 개발 |
| `sqs` | SQS에 메시지 보내고 Worker가 소비 | Worker Task가 따로 있을 때 |

현재 ECS 환경: `inline` 모드 (Worker Task `desired=0`인 상태에서도 동작)

---

## 5. S3 저장 경로

```
s3://bada-dev-evidence/cases/{날짜}_{사업장축약}_{case_id[:8]}/{파일명}
```

예시:
```
cases/20260618_○○제조_85cace2f/녹음파일.wav
```

- 날짜: 업로드 시점 (YYYYMMDD)
- 사업장: Case.workplace_name의 처음 6자 (특수문자 제거)
- case_id: UUID 앞 8자리 (고유성 유지)

---

## 6. 지원 언어 코드 (Transcribe)

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

## 7. 기존 파이프라인 통합

- `Evidence.ocr_text`에 전사 텍스트 저장 → 이미지/PDF OCR과 **동일 필드**
- `process_case` 실행 시 오디오 Evidence도 분석 컨텍스트에 포함
- DB 스키마 변경 없음 — `file_type="audio"` 값만 새로 사용
- 카테고리는 `audio` (프론트 업로드 카드에서 선택)

---

## 8. 에러 처리

| 실패 유형 | 처리 |
|-----------|------|
| Transcribe 잡 실패 | ocr_status="failed", 사유 로깅 |
| 10분 타임아웃 | ocr_status="failed", reason="timeout" |
| S3 접근 오류 | ocr_status="failed" |
| 빈 전사 결과 (무음) | ocr_text="", ocr_status="done" (유효) |
| Claude 후처리 실패 | Transcribe 원문 유지 (graceful degradation) |
| Vocabulary 생성 실패 | Vocabulary 없이 전사 진행 |
| 채널 식별 실패 (모노) | 화자 분리(diarization) 폴백 |

- 자동 재시도 없음 (사용자가 UI에서 "다시 시도" 클릭)

---

## 9. 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `PROVIDER_MODE` | local | 전체 provider 모드 (local=Mock, aws=실제) |
| `TRANSCRIPTION_DISPATCH_MODE` | inline | inline=백엔드 직접 처리, sqs=Worker 위임 |
| `AWS_REGION` | ap-northeast-2 | Transcribe/Bedrock 리전 |
| `S3_BUCKET` | | 오디오 파일 저장 버킷 |
| `BEDROCK_MODEL_ID` | global.anthropic.claude-sonnet-4-6 | Claude 후처리 모델 |

ECS 환경 예시 (Secrets Manager):
```
provider_mode=aws
transcription_dispatch_mode=inline
s3_bucket=bada-dev-evidence
```

---

## 10. 프론트엔드

- 업로드 카드: 🎤 "음성 녹음" (accept: audio/*, .m4a 포함)
- **다중 파일 선택** 지원 (순차 업로드, "2/5 업로드 중..." 표시)
- 전사 상태 폴링:
  - `processing` → "⏳ 음성을 텍스트로 변환 중입니다"
  - `done` → 화자별 텍스트 표시 (사업주/노동자 구분 스타일)
  - `failed` → 에러 메시지 + "다시 시도" 버튼

---

## 11. 테스트

```bash
cd worker && python -m pytest tests/ -v -k "transcri"
```

- MockTranscriber: 100ms 이내 고정 응답 → 로컬 E2E 동작
- 실제 전사: `PROVIDER_MODE=aws` + S3 버킷 설정 필요
- AWS 실측: S3 업로드 ✅, Transcribe 잡 생성 ✅, 결과 가져오기 ✅, Claude 후처리 ✅

---

## 12. 알려진 제한 및 대응

| 제한 | 원인 | 대응 |
|------|------|------|
| 모노 파일 화자 분리 부정확 | Transcribe 한국어 diarization 한계 | Claude가 맥락 기반 화자 재분리 |
| 배경 소음 시 인식률 하락 | 8kHz 전화 품질 한계 | Custom Vocabulary + Claude 교정 |
| Vocabulary 한국어만 | Transcribe Custom Vocab 제약 | 타 언어는 Vocabulary 없이 진행 |
| 음악/비대화 인식 불가 | STT 자체 한계 | 대화 녹음 전용으로 안내 |
| 첫 전사 시 Vocabulary 미적용 | PENDING→READY 전환 시간 | 두 번째부터 적용, 첫 건은 Claude가 보정 |

---

## 13. 아키텍처 결정 기록

| 결정 | 근거 |
|------|------|
| Transcribe + Claude 2단계 | Transcribe만으로는 화자 분리·정확도 부족. Claude가 맥락 기반 보정 |
| 채널 식별 우선 | 스테레오면 물리적 분리가 가장 정확. 모노만 AI 폴백 |
| Custom Vocabulary 자동 생성 | 팀원·환경별 수동 등록 불필요. 코드가 관리 |
| inline 디스패치 기본 | Worker 미구현 시에도 동작. SQS 전환은 환경변수 1개 |
| "사업주/노동자" 라벨 | Speaker 0/1보다 의미 있음. 증거 분석에 직접 활용 가능 |
| S3 경로에 날짜+사업장명 | UUID만으로는 콘솔에서 식별 불가. 디버깅 편의 |
| graceful degradation | Claude 실패 시 원문 유지. 전사 자체가 중단되면 안 됨 |
