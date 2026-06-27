# BADA 내부 동작 원리 (파일별 상세)

> 한 문장 원칙: **읽기·문장화·번역만 LLM이 하고, 계산·정렬·판정·대조는 전부 규칙 코드가 한다.**
> 이유: 돈·법이 걸린 서비스라 같은 입력엔 항상 같은 결과가 나와야 하고(결정론), 모든 판정에 근거(산식)를 댈 수 있어야 한다.

---

## 0. 큰 그림 — 요청 한 건이 흐르는 길

```
[사용자] 사진 업로드
   │  POST /cases/{id}/evidences/upload
   ▼
[backend/routers/evidences] → storage 저장 → DB Evidence(pending)
   │  POST .../extract
   ▼
[ocr_service] 파일 읽기 → [worker/providers/ocr] 엔진 선택
   │                          └ Claude Vision / Upstage → [_bedrock]/[_upstage]
   │                          └ [schema] 로 검증·정규화
   ├ PII 마스킹 · sanity 모순검사 · 근거 confidence 계산
   ▼  (엔티티를 DB에 저장, 사용자가 화면에서 수정 → PATCH /entities)
   │  POST .../analyze
   ▼
[analysis_service] 저장된 엔티티로 ctx 구성 → [worker/pipeline.process_case]
   │   ├ wage(차액) deductions(공제) missing(누락) geofence(GPS)
   │   ├ compare(증거 대조) legal(법령 점검)
   │   ├ timeline(타임라인) translation(번역대조표)
   │   └ summary(LLM 문장화) → guardrails(금지표현 차단)
   ▼
결과 JSON → DB 저장 → 프론트 결과화면 / 제출용 report.html
```

핵심: **읽기(OCR)와 판정(분석)이 분리**돼 있다. 그 사이에 사용자가 값을 고치는 단계(HITL)가 낀다.

---

## 1. 데이터 모델 — `backend/app/models.py`

DB 테이블 정의만 둔다(계산은 안 함). SQLAlchemy ORM.

- **User**: 사용자(이메일, 선호 언어).
- **Case**: 사건 1건(사업장명, 근무기간, 약속 시급, 문제유형, 상태 draft/analyzing/completed).
- **Evidence**: 증거 파일 1개. `category`(contract/statement/payment/chat/other), `ocr_status`(pending→processing→done/failed), `ocr_text`(읽은 원문), **`extracted_entities`(JSON, OCR이 뽑은 구조화 값 — 이게 모든 분석의 입력)**.
- **TimelineEvent**: 타임라인 1줄(날짜, 유형, 설명, 번역, **source_evidence_id**=출처, confidence).
- **TranslationPair**: 원문↔모국어 번역 대조표 1행.
- **AnalysisResult**: 분석 결과(기대급여·실수령·미지급의심·공제·`calculation_detail` JSON에 타임라인/대조/법령 등 통째 저장·요약).
- **Workplace / GpsLog**: 지오펜스 중심점·반경, GPS 핑(is_mocked=조작핑 표시).

원리: 모든 테이블이 `case_id`로 묶인다. 분석은 "이 사건의 Evidence들"을 모아 수행.

---

## 2. 백엔드 진입 · 공통

- **`main.py`**: FastAPI 앱 생성, 라우터(cases/evidences/analysis/gps) 등록, `static/` 서빙(프론트), 에러 핸들러 등록.
- **`config.py`**: `.env`를 절대경로로 읽어 `Settings`로 노출(`provider_mode`, `structured_engine`, `bedrock_model_id`, `upstage_api_key`…). 워커가 `os.environ`으로 읽으므로 **setdefault로 환경변수에 다리(bridge)를 놓는다** — 백엔드 설정 1곳만 바꾸면 워커도 따라온다.
- **`db.py`**: SQLAlchemy 엔진/세션(`get_db` 의존성). `DATABASE_URL`로 SQLite↔Postgres 교체.
- **`errors.py`**: 예외를 잡아 통일된 JSON 에러로 변환 + 로깅.
- **`services/storage.py`**: 파일 저장 추상화. 로컬=디스크, AWS=S3(`s3.py`). 업로드 시 `save(key,bytes)`, OCR 시 `read(key)`.

---

## 3. 라우터 (HTTP 엔드포인트) — `backend/app/routers/`

- **`cases.py`**: 사건 생성/조회. 프론트 "사건 정보" 입력이 여기로.
- **`evidences.py`**:
  - `POST /upload` 파일 받아 storage 저장 + Evidence(pending) 생성.
  - `POST /extract` → `ocr_service.run_ocr_on_case` 호출(실제 OCR).
  - **`PATCH /{eid}/entities`** → 사용자가 고친 값 저장(`ocr_service.update_entities`). HITL의 백엔드 끝단.
  - `DELETE`.
- **`analysis.py`**:
  - `POST /analyze` → `analysis_service.run_analysis` → 결과를 AnalysisResult/TimelineEvent/TranslationPair로 **저장** 후 반환(+면책문).
  - `GET /analysis` → 저장된 결과 재조회(`calculation_detail`에서 꺼냄).
  - `GET /report.html` → 제출·인쇄용 HTML 리포트(법정 기준 점검 섹션 포함).
- **`gps.py`**: GPS 로그 관련.

원리: 라우터는 **얇다**. HTTP만 받고 실제 일은 services로 넘긴다.

---

## 4. 백엔드 서비스 (오케스트레이션 글루)

### `services/ocr_service.py` — OCR 실행
- `run_ocr_on_case`: 사건의 Evidence들을 돌며,
  1. **캐싱**: 이미 `done`이면 재OCR 안 함(비용 절약).
  2. `storage.read` → `get_ocr(category).extract()`로 읽기.
  3. **PII 마스킹**(`_mask_chat`): 카톡/기타는 계좌·주민번호·전화 자동 마스킹(제3자 보호).
  4. 엔티티·원문을 DB에 저장(status=done/failed).
  5. 모든 추출이 끝난 뒤 **교차신호 계산**(`_cross_for_case`: 시급이 2건 이상에서 일치/불일치) → 각 행에 **sanity**(모순), **confidence**(근거 신뢰도), **evidence_quality**(카톡 증거력) 부착.
- `update_entities`: 사용자가 고친 엔티티 저장 → done 처리 → sanity·confidence **재계산**해서 갱신된 행 반환.

### `services/analysis_service.py` — 분석 입력 구성
- 저장된 Evidence 엔티티를 모아 **ctx**(분석 컨텍스트)를 만든다:
  - 시급/시간/입금/공제는 **수동입력(req) 우선, 없으면 OCR 추출값** 사용.
  - 카톡 발화(utterances)를 타임라인 입력으로 변환(출처 id 부착).
  - 증거 엔티티 묶음을 compare/legal용으로 전달.
- 그리고 `worker/pipeline.process_case(case_id, ctx)` 호출. **여기서부터 worker(규칙 엔진) 세계.**

---

## 5. 워커 — 읽기 계층 (`worker/providers/`)

### `ocr.py` — 엔진 라우팅 + 추출
- `get_ocr(category)`: 로컬이면 **MockOcr**(빈 결과). AWS면 카테고리로 분기:
  - 정형(contract/statement/schedule) → `_structured_provider()`: 키가 있으면 Upstage/Parseur, 없으면 **Claude Vision**.
  - 비정형(chat/other)·기본 → **ClaudeVisionOcr**.
- **ClaudeVisionOcr**: 이미지/PDF를 그대로 Claude에 넘겨 1샷으로 raw_text+엔티티 추출.
- **UpstageOcr/ParseurOcr**: 정형문서를 표/텍스트로 뽑은 뒤, 그 텍스트를 Claude Text로 한 번 더 구조화(2단계).
- 원리: **엔진마다 강점이 다르다** — 표·셀은 Upstage, 맥락·발화자는 Claude Vision. 자동 강등은 안 하고 키 없으면 Vision으로.

### `_bedrock.py` — Amazon Bedrock 호출 헬퍼
- `file_block`: 바이트가 PDF면 document, 아니면 image 블록으로 자동 변환.
- `invoke(system, blocks)`: `invoke_model`로 Claude 호출(`anthropic_version: bedrock-2023-05-31`).
- **`extract_json`**: 응답에서 JSON을 파싱해 `OcrResult`로 **검증**. 실패하면(잘림 등) max_tokens 늘리고 "raw_text 짧게"로 **재시도**. → OCR이 깨져도 최대한 살림.

### `_upstage.py` / `_parseur.py`
- Upstage Document Parse API 호출(`requests`), 429(레이트리밋) 시 백오프 재시도.

### `schema.py` — 출력 검증·정규화 (Pydantic)
- LLM 출력은 형식이 들쭉날쭉 → **관대하게** 받는다.
  - `_to_int`: `"1,795,680원"`·`null`·`""` → 정수 또는 None.
  - `_to_float`/`_to_bool`("예/없음" → True/False).
  - `kind`가 이상하면 "other"로.
- `ExtractedEntities`: dates/amounts/hourly_wage/deductions/utterances + **확장필드**(overtime/night/holiday_hours, work_days, contract_start/end, signed).
- 원리: **검증 실패로 통째 버리는 걸 막는다**(추출 성공률↑). 못 읽은 값은 None.

### `llm.py` / `translate.py`
- `get_llm`: 로컬=Mock(입력을 그대로 돌려줌), AWS=Bedrock Claude. **문장화 전용**(summarize_event/summarize_case).
- `get_translator`: 로컬=Mock, AWS=Amazon Translate. 한국어↔모국어.

---

## 6. 워커 — 판정 계층 (`worker/rules/`) **★ 시스템의 심장**

전부 **순수 함수 + 규칙**. LLM 호출 없음. 그래서 테스트 가능하고 결정론적.

- **`wage.py`** — 차액 계산. `기대급여 = 시급 × 근무시간합`, `미지급의심 = 기대 − 입금합`. 시급/시간이 불충분하면 계산 안 하고 "확인 필요"로 넘김(억지 계산 금지).
- **`deductions.py`** — 공제 분류. 사전(LEXICON)으로 "방값/dorm"→기숙사비처럼 표기 변형을 정규화 + "계약서 명시 확인 필요" 플래그.
- **`missing.py`** — 누락 안내. 업로드된 카테고리 집합에 없는 항목(통장/근무표/계약서/카톡)을 안내.
- **`geofence.py`** — GPS 정황. `haversine_m`로 근무지 반경 안/밖 판정, **조작핑(is_mocked) 배제**, 카톡 "도착" 시각과 ±30분 내 IN_WORKPLACE 핑이 겹치면 교차일치.
- **`compare.py`** — 증거 대조(검증포인트). 계약 시급↔명세서 시급, 명세서 실지급↔통장 입금합. match/mismatch/missing + 차액. **서로 다른 문서를 맞대보는 게 ProofPack의 핵심 가치.**
- **`sanity.py`** — 타당성(모순) 검사. 통상임금<기본급, 실지급>지급총액, 지급계−공제계≠실지급. **OCR 두 번 안 돌리고 오독을 잡는 무료 검증.**
- **`confidence.py`** — 근거 신뢰도. LLM 자기보고 대신 **교차일치(high)·sanity연루(low)·단일출처(medium)**로 필드별 등급. 낮은 필드를 화면에서 강조하기 위함.
- **`chat_evidence.py`** — 카톡 증거력. 상대식별·날짜·맥락(3줄+)·지급약속문장·금액 5개 체크리스트 채점 + 보강 안내.
- **`guardrails.py`** — 금지표현 필터. "불법/체불 확정/무조건 받음" → 중립 문구로 치환. "확정 아님"처럼 안전한 문장은 오탐 안 하도록 경계 정규식.
- **`legal.py`** — 법령 산식 매핑. 노동법 기준을 상수·공식으로:
  - `check_minimum_wage`: 시급 < 연도별 최저임금(2026=10,320) → 부족액.
  - `expected_premium_pay`: 연장·야간·휴일 가산분(0.5배) 추정.
  - `check_insurance_over_deduction`: 4대보험 공제가 표준요율의 1.5배 초과면 과다공제 의심.
  - `legal_review`: ctx에서 위 셋을 모아 findings 리스트로.

---

## 7. 워커 — 조립 계층 (`worker/services/`)

- **`extract.py`** (`aggregate`): 여러 Evidence 엔티티를 분석용 한 덩어리로 합침(시간·입금·공제·시급·사업장명 모으기).
- **`timeline.py`** (`build_timeline`): 근무시작·입금·**카톡 발화**·미지급의심·GPS를 날짜순 정렬 → LLM으로 한 문장씩 자연스럽게 + 번역. 각 이벤트에 출처 id·confidence 부착.
- **`translation.py`** (`build_translation_pairs`): 공제·미지급 같은 핵심 사실을 "원문→모국어" 대조표로.

---

## 8. 오케스트레이션 — `worker/pipeline.py`

`process_case(case_id, ctx)`가 위 규칙들을 **정해진 순서로** 호출해 하나의 결과 dict를 만든다:
1. (이미지 직접 전달 시) OCR → 2. wage/deductions/missing/geofence → 3. compare → 3-1. **legal** → 4. translation → 5. timeline → 6. summary(LLM, 실패 시 폴백) → **guardrails로 단정표현 차단**.
원리: **LLM/번역/OCR가 실패해도 규칙 결과는 항상 반환**(폴백). 분석이 빈손으로 끝나지 않는다.

---

## 9. 프론트엔드 — `backend/app/static/index.html`

순수 HTML/CSS/JS 단일 파일(폰 목업 형태) SPA.
- **상태**: `S={lang,caseId,analysis,ext}`. `api(method,path,body)` 한 함수로 백엔드 호출.
- **화면 전환**: `goPage(id)`로 home/newcase/upload/analyze/result/chat 토글.
- **업로드**: 카테고리별 📷촬영/파일. 업로드 전 `preprocessImage`로 **EXIF 회전 보정·다운스케일·JPEG 압축**, 해상도 낮으면 경고.
- **추출 결과**: `renderCard`가 추출값을 **편집 가능한 입력칸**으로 렌더. 저신뢰 금액은 노란색 ⚠. **"수정 저장"** → PATCH → 카드 다시 그림(sanity·confidence 재계산 반영).
- **분석**: `buildReq`로 폼을 요청으로 만들어 `/analyze` 호출, 진행바 애니메이션 후 `renderResult`.
- **결과**: 미지급의심 금액·요약·금액비교·검증포인트·**⚖️법정 기준 점검**·공제·GPS·타임라인(확인필요·출처)·누락 안내. 차이 없으면 헤드라인 과장 안 함.
- **i18n**: `T` 딕셔너리(ko/en/vi), `data-k` 속성으로 일괄 치환.

---

## 10. 측정 — `eval/`

- **`harness.py`**: gold 라벨로 **규칙엔진** 정확도(기대급여·차액·공제·누락)를 회귀 검증.
- **`ocr_score.py`**(신규): gold 엔티티 vs 추출 엔티티로 **OCR 필드 단위 정확도**(시급·금액·공제·확장필드)를 % 리포트. `--live`면 실제 OCR 돌려 비교.
- `dataset/ocr/*.json`: 정답 라벨 샘플.

---

## 11. 프롬프트 — `prompts/`

`extraction.md`(추출), `classification.md`(분류), `summary.md`·`timeline.md`(문장화). 코드와 분리해 **프롬프트만 따로 수정**할 수 있게. ocr.py가 `extraction`을 읽어 `{{category}}`를 치환해 사용.

---

## 한 줄 요약

> 읽기는 AI에게 맡기되, **돈과 법에 관한 모든 숫자·판정은 규칙 코드가 책임진다.**
> 그래서 결과가 항상 같고, 왜 그런지 근거를 댈 수 있고, 사용자가 틀린 값을 고칠 수 있다.
