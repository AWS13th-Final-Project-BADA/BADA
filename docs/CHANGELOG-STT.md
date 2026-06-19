# 음성 인식(STT) 변경 이력

---

## 2026-06-19: Claude 후보정 제거 + 엔티티 추출 분리

### 배경

피드백: "음성 녹음은 증거이므로, AI가 텍스트를 보정하면 증거로서의 가치를 잃을 수 있다."

기존 구현에서는 Transcribe 원문을 Bedrock Claude로 후처리하여:
1. 텍스트 교정 (오인식 수정, 조사/어미 복원)
2. 맥락 기반 화자 재분리 ("사업주:" / "노동자:" 라벨링)

을 수행한 뒤, **보정된 결과를 `ocr_text`에 덮어쓰고** 있었다.

### 문제

- 원본 전사 텍스트가 사라짐 → "실제로 뭐라고 했는가" 확인 불가
- AI가 교정한 텍스트는 원본과 다를 수 있음 → 법적 증거 가치 훼손
- 화자 라벨("사업주/노동자")은 AI 추정일 뿐인데, 원문처럼 보임

### 변경 내용

#### 1. Claude 후보정 완전 제거

| 삭제된 코드 | 위치 |
|------------|------|
| `refine_transcript()` 함수 | `worker/services/transcription.py` |
| `_REFINE_SYSTEM`, `_REFINE_PROMPT` | 동일 파일 |
| `process_transcription()` 내 Claude 호출 | 동일 파일 |

Transcribe 원문이 `ocr_text`에 그대로 저장된다.

#### 2. 엔티티 추출을 별도 레이어로 분리

전사 완료 후, **원문을 변형하지 않고** Claude Text로 엔티티만 구조화하여 `extracted_entities`에 저장.

```
Evidence
├─ ocr_text            ← Transcribe 원문 (증거, 불변)
└─ extracted_entities  ← Claude가 읽어서 구조화 (분석용)
     ├─ amounts, hourly_wage, monthly_wage
     ├─ deductions, dates, pay_date
     ├─ utterances (speaker, text, kind)
     ├─ work_days, overtime/night/holiday_hours
     └─ workplace_name, employer_name
```

#### 3. 음성 전용 엔티티 추출 프롬프트 추가

| 변경 파일 | 내용 |
|-----------|------|
| `worker/providers/ocr.py` | `_instruction("audio")` 분기 추가 |

프롬프트 특징:
- STT 대화 원문임을 명시
- Speaker 0/1 라벨 인식
- 발화 분류 강조 (wage_promise, underpayment_admit, evasive 등)
- "대화에서 직접 언급되지 않은 값은 지어내지 마세요"

#### 4. `/extract` 엔드포인트 오디오 지원

| 변경 파일 | 내용 |
|-----------|------|
| `backend/app/services/ocr_service.py` | `audio_targets` 목록으로 전사 완료+엔티티 미추출 Evidence 처리 |

기존에는 `run_ocr_on_case()`가 image/pdf만 대상이었으나, 이제 오디오도 포함.

### 변경된 파일 목록

| 파일 | 변경 |
|------|------|
| `worker/services/transcription.py` | `refine_transcript()` 삭제, Claude 프롬프트/import 제거 |
| `worker/providers/ocr.py` | `_instruction()` audio 분기 추가 |
| `backend/app/routers/evidences.py` | `_extract_entities_from_text()` 추가, docstring 업데이트 |
| `backend/app/services/ocr_service.py` | `audio_targets` 엔티티 추출 로직 추가 |
| `docs/SPEECH-TO-TEXT-HOW-IT-WORKS.md` | 전면 재작성 |

### 설계 원칙 (이번 변경으로 확립)

1. **증거 무결성**: `ocr_text`는 Transcribe 원문 그대로. AI 보정/교정 없음.
2. **분석은 별도 레이어**: `extracted_entities`에 구조화 결과 저장. 원문과 분리.
3. **실패 격리**: 엔티티 추출 실패해도 전사 자체는 성공 유지 (`ocr_status=done`).
4. **HITL**: 사용자가 추출값을 수정 가능 (PATCH /evidences/{eid}/entities).
5. **화자 라벨**: Speaker 0/1 (익명) 유지. "사업주/노동자" 판별은 사용자 몫.

### 남은 것 (Phase 2)

- 사용자가 UI에서 Speaker 0 = "사업주", Speaker 1 = "노동자"로 지정하는 기능
- SQS handler(`worker/handlers/transcription.py`)에 동일 로직 연결 (현재 TODO)
- 오디오 엔티티 추출 정확도 평가셋 구축

---

## 이전 설계 (참고용, 더 이상 적용되지 않음)

```
[Transcribe] → 원문 → [Claude 후처리] → 보정본 → ocr_text 저장
                         ├─ 텍스트 교정
                         └─ 화자 재분리 ("사업주:"/"노동자:")
```

폐기 사유: 증거 원문이 AI에 의해 변형되어 법적 증거 가치 훼손 우려.
