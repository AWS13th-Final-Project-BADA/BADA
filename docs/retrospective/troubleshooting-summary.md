# 트러블슈팅 종합 (회고용)

> 발표/회고를 위해 프로젝트 전 기간의 트러블슈팅 기록을 종합한 문서다.
> 원본 상세는 각 항목의 "원본" 링크에서 확인할 수 있다. 이 문서는 발표에 쓸 수 있도록
> 증상 → 원인 → 해결을 짧게 압축했다.

## 목차

1. [증거수집 에이전트 (모바일)](#1-증거수집-에이전트-모바일)
2. [OCR / Bedrock 파이프라인](#2-ocr--bedrock-파이프라인)
3. [분석 파이프라인 / 백엔드](#3-분석-파이프라인--백엔드)
4. [Transcribe / STT](#4-transcribe--stt)
5. [인프라 / 배포](#5-인프라--배포)
6. [모바일 빌드 / 개발환경](#6-모바일-빌드--개발환경)
7. [개발 툴링 (MCP, 로컬환경)](#7-개발-툴링-mcp-로컬환경)

---

## 1. 증거수집 에이전트 (모바일)

### 1-1. 4단계 서버 OCR이 트리거되지 않음 / 정확도 낮음

**증상**: 온디바이스 1~3단계(메타필터·키워드 스코어)는 정상 동작하지만, 서버 4단계(Bedrock OCR)가 실행 안 되거나 결과가 부정확함.

**원인**: `agent.ts`의 `uploadApprovedCandidates()`가 ①`category="other"`로 고정 업로드해 정형 문서(명세서·계약서)도 카톡 발화 추출 프롬프트를 탔고, ②업로드 후 `/extract` 호출 자체가 없어 `ocr_status="pending"`으로 방치됨.

**해결**: `category="auto"`로 변경(서버 `classify`가 문서 종류 자동 판별) + 업로드 후 `/extract`를 fire-and-forget으로 트리거.

**PR**: #169 (`fix/agent-bedrock-ocr-trigger`)

### 1-2. 증거 0개 수집 — 퇴직 후 캡처 증거 누락 (과거 이슈)

**증상**: 갤러리 스캔 후보가 0개로 나옴.

**원인 분석**: 1차로 "앱 재설치로 갤러리 권한이 제한된 접근으로 리셋됨"이 유력 원인으로 확인됐고, 별개로 `endDate`를 `work_end_date`(퇴직일) 기준으로 계산하고 있어 **퇴직 후 캡처한 카톡/스크린샷 증거가 날짜 필터에서 원천 배제**되는 구조적 문제를 발견.

**해결**: `endDate`를 항상 `new Date()`(현재 시점)로 고정. 시작일(`work_start_date - 30일`)만 유지.

**PR**: #173 (`fix/agent-scan-enddate`)

### 1-3. 사건 상세 화면에서 진입 시 근무 시작일이 무시됨 (오늘 발견, 2026-07-03)

**증상**: 사건 상세 → 업로드 화면으로 들어가서 "AI 증거 탐색"을 실행하면, 실제 근무 시작일(예: 2025-03-09)과 무관하게 좁은 날짜 범위(폴백값 `2026-01-01` 기준)만 스캔됨.

**원인**: `upload.tsx`가 `routeCaseId`(사건 상세에서 넘어온 경로)가 있을 때는 `cases` 목록을 API로 불러오지 않았음. 그 결과 `selectedCase`(`cases.find(...)`)가 항상 `null`이 되어 `caseData?.work_start_date`가 매번 `undefined` → 폴백 날짜만 사용됨. 사건 상세를 거쳐 들어가는 **정상적인 사용 흐름에서 항상 발생**하던 버그.

**해결**: `routeCaseId` 유무와 무관하게 항상 사건 목록을 불러오도록 수정.

**PR**: #236 (`fix/agent-scan-date-filter-and-case-load`)

### 1-4. 카톡/메신저로 받은 이미지가 날짜 필터에서 통째로 누락 (오늘 발견, 2026-07-03)

**증상**: 갤러리에 16장이 있는데 4장만 스캔됨. 누락된 12장은 실제로는 스캔 대상 기간(예: 2026년 6월) 내 파일인데도 걸러짐.

**원인**: `MediaLibrary.getAssetsAsync`에 `createdAfter`/`createdBefore`를 넘기면 Android 네이티브 구현이 `MediaStore.Images.Media.DATE_TAKEN`(촬영 EXIF) 컬럼만으로 필터링함(`GetAssetsQuery.kt`). 카톡/메신저/파일공유로 전달받은 이미지는 EXIF가 없어 `DATE_TAKEN`이 0/NULL로 남는 경우가 흔해, 실제로 최근에 받은 파일인데도 통째로 걸러짐.

**해결**: 날짜 필터를 네이티브 쿼리에 넘기지 않고 전체를 가져온 뒤, JS에서 `creationTime`(없으면 `modificationTime`)으로 직접 필터링.

**PR**: #236 (`fix/agent-scan-date-filter-and-case-load`)

> 진단 과정에서 로컬 Android 빌드(`expo run:android`) 환경도 함께 구축함 — Java 24가 기본이라 Gradle 8.8이 빌드 스크립트를 해석 못 하는 문제, 기존 EAS 서명과 로컬 debug 서명 불일치로 인한 재설치 실패(1-11 참고)도 같은 세션에서 해결.

### 1-5. 파일명/경로 키워드 기반 후보 선정의 구조적 정확도 한계

**증상**: "AI 증거 탐색" 결과에 셀카, 기프티콘 바코드, 예약 캡처 등 무관한 파일이 "추천"으로 표시됨. 반대로 실제 증거 사진이 파일명에 키워드가 없으면 후보에서 누락됨.

**원인**: Expo managed workflow에서 온디바이스 OCR(ML Kit)을 못 써서, 2~3단계가 파일명·경로 문자열 매칭(`EVIDENCE_KEYWORDS`, "screenshot"/"kakao"/"download" 포함 여부)으로 대체되어 있음. 내용을 못 보고 이름·경로만 보니 카톡 폴더에 있으면 내용 무관하게 무조건 통과(+0.3), 스크린샷 폴더도 마찬가지(+0.2).

**대응**: 사용자 확인 체크리스트 단계를 제거하고 서버의 `classify`(Bedrock)가 최종 판별하도록 변경 — 디바이스 필터링은 서버 비용 절감용 사전 감축 역할로 한정.

**PR**: `feature/agent-auto-upload`

**상태**: 구조적 한계로 남음 → [향후 개선점](./future-improvements.md#에이전트--ocr) 참고.

### 1-6. 후보 리스트 스크롤 안 됨

**증상**: 후보 목록이 5~6개만 보이고 나머지를 볼 수 없음.

**원인**: 후보 리스트를 `<ScrollView maxHeight={240}>`로 감쌌는데, 바깥 화면 전체가 이미 `ScrollView`(`StitchScreen`)라 React Native 중첩 ScrollView 문제로 내부 스크롤 터치가 먹힘.

**해결**: 내부 `ScrollView`/`maxHeight` 제거, 후보를 일반 `View`로 펼쳐 바깥 스크롤로 탐색. 20장 제한(`slice(0,20)`)과 스캔 500장 제한도 함께 제거.

**PR**: `fix/agent-remove-limits`

### 1-7. 증거 업로드 시 ExifInterface 권한 에러

**증상**: "선택 파일 등록" 시 `Cannot access ExifInterface because of missing ACCESS_MEDIA_LOCATION permission`으로 업로드 실패.

**원인**: Android 10(API 29)+에서 이미지 EXIF의 GPS 메타데이터 접근에는 `ACCESS_MEDIA_LOCATION` 권한이 별도로 필요한데 `app.json`에 선언이 없었음.

**해결**: `app.json`의 Android `permissions`에 `ACCESS_MEDIA_LOCATION` 추가.

**PR**: `fix/media-location-permission`

### 1-8. 업로드 UX 개선 (파일 리스트/미리보기)

**증상**: 증거가 수백 개면 리스트 전체를 스크롤해야 분석 버튼이 보이고, 미리보기가 문서 아이콘+파일명뿐이라 식별이 어려움.

**해결**: 리스트 최대 5개 표시 + "N개 더 보기/접기" 토글, 이미지 실제 썸네일 렌더링, 업로드/분석 버튼을 리스트 위쪽으로 이동, 스캔 완료 시 Alert 없이 분석 화면으로 즉시 이동(자동 4단계 진행, 사후 검증 흐름).

---

## 2. OCR / Bedrock 파이프라인

### 2-1. OCR entities 빈 값 반환 — 원인 규명까지의 과정

**증상**: Claude Vision이 `raw_text`(원문)는 완벽하게 추출하는데 `entities`(시급, 금액, 발화 분류 등 구조화 필드)가 전부 `null`/빈 배열로 반환됨. `contract`/`chat`/`statement` 카테고리 가리지 않고 공통 증상.

**1차 진단(추정)**: `ClaudeVisionOcr.extract()`가 1-pass 구조(이미지→읽기+구조화 동시 지시)라, Vision 모델이 "읽기"엔 강해도 즉시 필드 매핑은 불안정하다는 가설. 2-pass(Vision→raw_text만 → Text 모델로 entities 구조화) 전환을 검토.

**근본 원인(실제)**: Worker Dockerfile에 `prompts/` 디렉토리가 누락돼 있었음(`COPY prompts /app/prompts` 없음). `extraction.md` 프롬프트가 이미지에 없어 `_instruction()`이 항상 except fallback(간략 프롬프트)으로 동작 — **entities 구조화 도입 이후 프롬프트가 한 번도 제대로 로드된 적이 없었음**.

**해결**: `COPY prompts /app/prompts` 추가, `extraction.md`에 "entities 빈 값 금지" 규칙 명시, flat JSON 응답 정규화(entities 래핑 없이 와도 흡수) 추가. 이 근본 수정 이후 2-pass 전환 없이 **1-pass로 복귀**해도 정상 동작함을 확인(비용·지연 절감).

**PR**: #144(Dockerfile 수정), #150(flat JSON 흡수), #152(1-pass 복귀)

**원본**: `docs/troubleshooting/changelog-20260630.md`

### 2-2. 업로드 카테고리 디폴트가 "contract"로 고정

**증상**: 카톡·신고서 등 다양한 파일을 올려도 전부 `category="contract"`로 저장돼, OCR 프롬프트가 "계약서에서 시급 찾기"로 고정되며 카톡 이미지에서 빈 결과가 나옴.

**원인**: `upload.tsx`의 `category` state 초기값이 `"contract"`(카테고리 배열 첫 번째)였고, 업로드 후에도 초기화가 안 돼 사용자가 매번 바꿔야 한다는 걸 인지하지 못함. 카테고리 오분류는 `present_categories` 누락 판정 오류, 명세서-통장 대조 불가 등으로 연쇄됨.

**해결**: 디폴트를 `"auto"`로 변경 + 카테고리 배열 맨 앞에 `auto` 칩 추가. `auto` 업로드 시 서버 `classify`(Bedrock)가 문서 종류 자동 판별.

**PR**: `fix/upload-default-auto`

### 2-3. 이미지 다운스케일 — 분석 지연의 71%가 vision 호출

**증상**: "분석 실행" 스피너가 OCR 케이스에서 76초까지 걸림.

**원인**: CloudWatch/Bedrock 지표 실측 결과, `analyze_case` 76초 중 OCR(vision) 호출이 53.7초(71%)를 차지. Throttle/재시도가 아니라 **단일 vision 호출이 입력/출력 토큰 양에 비례해 느린 것**으로 확인(동시성 쿼터 상향은 무의미).

**해결**: Bedrock 전송 전 이미지를 다운스케일(긴 변 1568px 초과 시 축소 + JPEG q85 재인코딩). Claude Vision이 서버 측에서 어차피 1568px로 리사이즈하므로 인식 정확도 손실 없이 업로드 크기·토큰만 절감.

**PR**: #232

**원본**: `docs/troubleshooting/changelog-20260703.md`

### 2-4. Worker 로그가 CloudWatch에 안 찍힘 (미해결로 시작 → 조사 중 해소)

**증상**: Worker ECS 태스크가 Running인데 CloudWatch 로그 그룹에 최근 로그가 전혀 없음.

**원인 후보**: SQS 큐가 비어 long-polling 대기만 하고 있었을 가능성(출력 자체가 없음), 로그 드라이버/권한 설정 문제.

**상태**: 이후 Worker SQS consumer 상시 실행 및 로그 정상 확인(`implementation-status.md` "Worker SQS long-running consumer: 완료"). 당시엔 원인 특정 전이었음.

### 2-5. Worker `ModuleNotFoundError: No module named 'app.config'`

**증상**: SQS 분석 메시지 처리 시 Worker가 `app.config`를 못 찾아 분석 실패.

**원인**: `worker/Dockerfile`이 `models.py`, `db.py`, `__init__.py` 3개만 복사하고 `config.py`가 누락. `config.py`가 의존하는 `pydantic-settings`도 Worker `requirements.txt`에 없었음.

**해결**: `COPY backend/app /app/backend/app`로 전체 복사, `requirements.txt`에 `pydantic-settings` 추가.

### 2-6. 병렬 처리 성능 — Backend/Worker 동시성 불일치

**증상**: 증거 5~10장 분석에 5분 이상 소요.

**원인**: `backend/app/services/ocr_service.py`의 `ThreadPoolExecutor(max_workers=4)`가 병목. Worker 쪽은 이미 `max_workers=50`으로 병렬화됐지만 Backend 동기 경로(`/extract?wait=true`)만 4로 남아있었음.

**해결**: Backend `max_workers`를 4 → 30으로 상향(Bedrock 계정 한도 내 안전 범위). Worker 쪽은 메모리 여유(2048MiB 중 33% 사용, 마진 67%)를 근거로 50 유지.

**PR**: `fix/ocr-parallel-30`(Backend), #157(Worker 병렬화)

**원본**: `docs/infra/worker-sizing.md`, `docs/troubleshooting/changelog-20260630.md`

---

## 3. 분석 파이프라인 / 백엔드

### 3-1. `/analyze` 저장 시 `could not convert string to float: 'high'`

**증상**: CI Backend API 테스트 5건이 `POST /cases/{id}/analyze`에서 공통 실패.

**원인**: `TimelineEvent.confidence` 컬럼이 `Numeric(5,4)`로 정의돼 있는데, 코드는 `"high"/"medium"/"low"` 문자열 enum을 저장하려 함. `domain.md`/`schemas.py` 스펙은 원래부터 문자열 enum이 맞고, **모델 컬럼 타입이 과거 설계 잔재로 틀려 있던 것**.

**해결**: `confidence: Mapped[str | None] = mapped_column(String(10))`로 수정. 1줄 수정, 데이터/마이그레이션 영향 없음(라이브 RDS 데이터 없던 시점).

**검증**: 변경 전 5 failed/27 passed → 변경 후 32 passed.

**후속 과제**: 같은 `Numeric(5,4)` confidence 컬럼이 `evidences`, `evidence_texts`, `analysis_results`, `evidence_relations` 4곳에 더 있음 — 현재는 ORM으로 값을 안 써서 안 터지지만, 사용 시작하면 재발 가능. [향후 개선점](./future-improvements.md#데이터모델) 참고.

**원본**: `docs/troubleshooting/timeline-confidence-type.md`

### 3-2. 타임라인 날짜 파싱 에러 — SQS 무한 재시도

**증상**: 특정 사건 분석 시 Worker가 계속 실패 → SQS 재시도 → DLQ 도달까지 반복.

**원인**: 타임라인 이벤트 날짜 파싱 로직이 특정 날짜 포맷을 처리 못 해 예외 발생, 재시도해도 같은 입력이라 계속 실패.

**원본**: `docs/troubleshooting/changelog-20260701.md` (상세 원인 로그는 원본 참고)

### 3-3. `chat_arrivals` 누락 — 비동기(Worker) 경로에서 GPS↔카톡 교차검증 0건

**증상**: SQS 경로(Worker `analyze_case`)에서는 GPS↔카톡 교차검증이 항상 0건. 동기 경로(`/analyze` API 직접 호출)에서는 정상.

**원인**: `worker/handlers/analysis.py`에서 `ctx["chat_arrivals"]`가 `[]`로 하드코딩. 동기 경로는 `req.chat_arrivals`를 외부에서 받지만, 비동기 경로는 DB의 카톡 발화에서 직접 추출하는 로직이 빠져 있었음.

**해결**: 카톡 발화(`chat_utts`) 중 `kind`가 도착/지급약속/근무지시인 항목의 날짜를 파싱해 `chat_arrivals`를 구성하도록 수정.

**PR**: `fix/pipeline-chat-arrivals`

### 3-4. SQS 메시지 적체 + DLQ 70건

**증상**: `bada-dev-analysis`에 38개 대기, `bada-dev-analysis-dlq`에 70개 누적. Backend는 정상 발행 중이나 Worker가 소비 못 함.

**원인 후보**: Worker 태스크 미기동/CrashLoop, 특정 메시지 타입 처리 실패, 처리 타임아웃.

**해결**: Worker 서비스 강제 재배포(force new deployment)로 정상화. `extract_ocr` 핸들러는 이미 최신 코드에 구현돼 있음을 확인.

### 3-5. PDF 생성 실패 — WeasyPrint 버전 버그

**증상**: `AttributeError: 'super' object has no attribute 'transform'`.

**원인**: WeasyPrint 62.3 내부 버그(`stream.py`).

**해결**: `weasyprint==62.3` → `weasyprint==63.0`로 업그레이드.

### 3-6. PDF presigned URL이 잘못된 버킷 참조

**증상**: PDF 다운로드 링크가 깨짐.

**원인**: presigned URL 생성 시 evidence 버킷(`bada-dev-evidence`)을 참조하고 있었음(정답은 report 버킷).

**해결**: `S3_REPORT_BUCKET` 환경변수를 우선 사용, 미설정 시 버킷명에서 추론(`-evidence`→`-report`). PDF 미생성 시 "생성 중" 표시, `pdf_ready=true`일 때만 다운로드 버튼 노출.

**원본**: `docs/troubleshooting/changelog-20260630.md`

---

## 4. Transcribe / STT

### 4-1. Mock 텍스트만 나옴 (Transcribe 실제 미호출)

**원인**: Secrets Manager에 `provider_mode=aws`가 없어 ECS `PROVIDER_MODE` 기본값 `"local"` → MockTranscriber 사용.

**해결**: Secrets Manager에 `provider_mode: aws` 추가. **교훈**: 로컬은 `.env`로 되지만 ECS는 Secrets Manager/Task Definition 환경변수에 명시해야 함.

### 4-2. Transcribe는 되는데 화자 분리(Claude 후처리)가 안 됨

**원인(3중)**:
1. `refine_transcript()`가 `PROVIDER_MODE`만 확인하고 `TRANSCRIBE_MODE`(독립 운영 변수)는 안 봄 → `PROVIDER_MODE=local`이라 건너뜀.
2. `deploy-dev.yml`의 `paths`에 `worker/**`가 없어 코드 수정해도 배포가 트리거 안 됨.
3. Task Definition은 갱신됐지만 기존 Task가 교체 안 됨(rolling update 미발생).

**해결**: `refine_transcript()`가 `TRANSCRIBE_MODE`를 참조하도록 수정, `workflow_dispatch` 수동 트리거(근본 해결은 `paths`에 `worker/**` 추가), `--force-new-deployment`로 Task 교체.

### 4-3. Custom Vocabulary 생성 실패 (AccessDeniedException)

**원인**: ECS Task Role에 `transcribe:CreateVocabulary`/`GetVocabulary` 권한 누락.

**상태**: 전사 자체는 Vocabulary 없이 정상 동작. 권한 추가는 별도 처리 필요.

### 4-4. 대량 업로드 시 S3에 파일이 안 올라감

**원인**: 이전 배포에서 `STORAGE_MODE=local`이었거나 S3 버킷명 오설정 상태로 업로드 → 컨테이너 로컬 디스크 저장 후 재시작 시 소실.

**해결**: Secrets Manager의 `s3_bucket` 설정 확인 후 재업로드.

**원본**: `docs/troubleshooting/transcribe-deploy-issues.md`

### 4-5. STT entities 미구조화

**원본**: `docs/troubleshooting/changelog-20260701.md` (상세는 원본 참고)

---

## 5. 인프라 / 배포

### 5-1. Grafana 메트릭 네임스페이스 불일치

**원본**: `docs/troubleshooting/changelog-20260701.md`

### 5-2. Container Insights 미활성화로 Grafana No Data

**원인**: ECS 클러스터에 `containerInsights=enabled` 설정이 없으면 Fargate CPU/Memory 메트릭이 CloudWatch로 전송 안 됨.

**해결**: Terraform으로 `containerInsights` 활성화.

**PR**: #156

---

## 6. 모바일 빌드 / 개발환경

### 6-1. EAS 빌드 Gradle 실패 — SDK 버전 불일치

**증상**: `Gradle build failed with unknown error`.

**원인**: `expo-media-library@^56.0.7`이 설치돼 있었으나 이 버전은 Expo SDK 52+ 전용, 프로젝트는 SDK 51.

**해결**: `expo-media-library@~16.0.5`(SDK 51 호환)로 재설치. **교훈**: managed workflow에서 네이티브 패키지 추가 시 `expo install <pkg>`로 SDK 호환 버전을 자동 매칭해야 함.

### 6-2. Expo Go QR 접속 실패 / 로그인 강제

**원인**: `app.json`의 `"owner": "dkdevelop"`이 EAS 계정 로그인을 강제, 동일 Wi-Fi 아니면 Metro 접근 불가, `--tunnel` 모드는 EAS 로그인 필수.

**해결**: 임시 계정(`bada-temp-build`)의 `EXPO_TOKEN`으로 독립 APK를 EAS Build로 제출해 Expo Go 없이 설치.

### 6-3. APK 설치 시 "기존 패키지와 충돌" (반복 발생 이슈)

**증상**: 새 APK 설치 시 `INSTALL_FAILED_UPDATE_INCOMPATIBLE` 계열 에러.

**원인**: 같은 패키지명(`com.bada.app`)이지만 **서명이 다른** 빌드가 이미 설치돼 있어 Android가 덮어쓰기를 거부. 이전엔 EAS 클라우드 빌드(계정 서명) vs 다른 계정 서명 간 충돌, 오늘(2026-07-03)은 기존 EAS 클라우드 빌드 vs 로컬 debug 빌드(`expo run:android`) 간 서명 불일치로 재발.

**해결**: 기존 앱 삭제(`adb uninstall com.bada.app` 또는 설정에서 삭제) 후 재설치. **반복 발생 패턴이므로 서명 체계를 통일하거나(예: 로컬 개발도 release 서명 사용) 팀 내 공유가 필요.**

### 6-4. Worker CPU/Memory 상향 (PDF 생성 성능)

**원인**: WeasyPrint 한글 폰트(fonts-noto-cjk, 15MB) 임베딩이 Fargate 0.5vCPU에서 ~50초 소요.

**해결**: Worker CPU 256→1024 units, Memory 512→2048 MiB로 상향, ~15초로 단축. 비용 +$8/2주.

**원본**: `docs/infra/worker-sizing.md`, `docs/troubleshooting/changelog-20260630.md`

---

## 7. 개발 툴링 (MCP, 로컬환경)

### 7-1. MCP terraform 서버 연결 실패

**증상**: Kiro IDE 시작 시 `npm error 404 Not Found - GET .../@hashicorp%2fterraform-mcp-server` 반복 출력.

**원인**: `.kiro/settings/mcp.json`에 등록된 `@hashicorp/terraform-mcp-server` 패키지가 실제로 npm registry에 공개돼 있지 않음.

**해결**: 해당 서버 항목을 `"disabled": true`로 변경. 이 파일이 Git 추적 대상이라 `git pull`로 원복될 수 있어 팀 전체 영향을 피하기 위해 로컬에서만 관리하기로 함.

### 7-2. 로컬 Android 빌드 시 Java 버전 불일치 (오늘 발견, 2026-07-03)

**증상**: `npx expo run:android` 시 `BUG! exception in phase 'semantic analysis' ... Unsupported class file major version 68`.

**원인**: 클래스 파일 버전 68 = Java 24. 시스템 기본 `java`가 Java 24(Temurin)로 잡혀 있어 Gradle 8.8이 자기 자신을 실행하지 못함(React Native/Expo 빌드는 Java 17 요구).

**해결**: 시스템 기본 Java를 바꾸지 않고, 빌드 명령에만 `JAVA_HOME`을 로컬에 이미 설치된 JBR 17(JetBrains)로 임시 지정해서 실행. 프로젝트 코드·팀 공유 설정은 변경하지 않은 개인 환경 조치.

### 7-3. awscli / botocore 버전 충돌

**증상**: `aws` 명령 실행 시 `ImportError: cannot import name 'register_feature_id' from 'botocore.useragent'`.

**원인**: `awscli 1.45.36`이 `botocore 1.35.99`와 호환 안 됨.

**해결**: `pip3 uninstall awscli botocore s3transfer -y && pip3 install awscli`로 재설치.

### 7-4. (과거) Capacitor 기반 모바일 프로토타입 관련 이슈

> 아래는 현재의 `mobile-native`(Expo) 이전, `mobile/`(Capacitor 기반) 프로토타입 시절 이슈. 참고용으로만 남김.

- `npx cap add android` 텔레메트리 응답 대기로 타임아웃 → `npx cap telemetry off` 실행 후 재시도.
- Android Studio Gradle 빌드 실패(`capacitor.settings.gradle` 없음) → `npx cap sync android` 미실행이 원인, `www/` 폴더 생성 후 sync.
- `@transistorsoft/capacitor-background-geolocation` 설치 실패 → 유료 플러그인이라 공개 레지스트리에 없음. 무료 `@capacitor/geolocation`으로 통일.

---

## 참고 — 미해결/조사 중으로 남았던 항목 (현재 상태 갱신)

| 항목 | 당시 상태 | 현재 상태 |
|---|---|---|
| Worker CloudWatch 로그 미출력 | 조사 중 | 해소 — Worker SQS consumer 상시 실행·로그 정상 확인 |
| OCR 2-pass 전환 | PR 진행 중 | 불필요 — 근본 원인(Dockerfile) 수정 후 1-pass로 복귀, 정상 동작 |
| 에이전트 디바이스 필터 정확도 한계 | 구조적 한계로 낮은 우선순위 | 여전히 미해결 — [향후 개선점](./future-improvements.md#에이전트--ocr) 참고 |

---

## 원본 문서 색인

| 파일 | 시기 |
|---|---|
| `docs/troubleshooting/timeline-confidence-type.md` | 2026-06-16 |
| `docs/troubleshooting/transcribe-deploy-issues.md` | STT 배포 시점 |
| `docs/troubleshooting/changelog-20260630.md` | 2026-06-30 |
| `docs/troubleshooting/changelog-20260701.md` | 2026-07-01 |
| `docs/troubleshooting/changelog-20260703.md` | 2026-07-03 |
| `docs/infra/worker-sizing.md` | 2026-06-30 |
| PR #169, #173, #236 (에이전트 스캔) | 2026-06 ~ 07-03 |
