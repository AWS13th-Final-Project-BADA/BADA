# 역할 분담 맵 (기능별 담당 · 파일 · 교체 지점)

> 공통 기반은 완성되어 있고 **로컬 mock으로 전체가 돌아간다**(AWS 불필요).
> 각 담당은 아래 "구현할 것"의 파일/클래스만 채우면 된다. 인터페이스는 고정 → 충돌 없이 병렬 작업.
> 실행: 루트에서 `./run.ps1` → http://localhost:8000 . 테스트: `cd backend && pytest`, `cd worker && pytest`.

## 공통 기반 (이미 완성 — 모두가 의존, 건드릴 때 합의)

| 영역 | 파일 | 상태 |
| --- | --- | --- |
| 설정/모드 | `backend/app/config.py`, `worker/config.py` | ✅ provider_mode/auth/storage 스위치 |
| DB 모델 | `backend/app/models.py` | ✅ 전체 테이블 |
| 스키마 | `backend/app/schemas*.py` | ✅ API/LLM 출력 |
| 규칙 엔진 | `worker/rules/*` | ✅ 테스트됨(차액·공제·누락·지오펜스) |
| 파이프라인 | `worker/pipeline.py`, `worker/services/*` | ✅ provider 호출 골격 |
| 인증 seam | `backend/app/deps.py` | ✅ 소셜 OAuth(구글/카카오/네이버) + 자체 JWT. Cognito는 미사용 레거시 |
| 스토리지 seam | `backend/app/services/storage.py` | ✅ 로컬FS, S3 교체점 |
| 에러/로깅 | `backend/app/errors.py`, `main.py` | ✅ |
| 프론트 | `backend/app/static/index.html` | ✅ 단일페이지(API 연결) |
| 시드/테스트 | `backend/seed.py`, `backend/tests/*`, `eval/*` | ✅ |

## 1) OCR 담당 — 이미지/문서 → 텍스트·엔티티

- **구현할 것**: `worker/providers/ocr.py` 의 `ClaudeVisionOcr.extract`, `UpstageOcr.extract`
- **참고**: `prompts/extraction.md`, 출력 스키마 `backend/app/schemas.py:OcrResult`, 라우팅 규칙은 같은 파일 상단
- **규칙**: Upstage 전송 전 `worker/security/pii.py:mask_pii` 적용. 스키마 검증+재시도(architecture.md).
- **연결**: `worker/pipeline.py` 1단계 루프에서 추출 엔티티를 ctx에 병합하도록 확장.
- **전환**: `PROVIDER_MODE=aws` 환경변수.

## 2) 타임라인/요약 담당 — 문장화

- **구현할 것**: `worker/providers/llm.py` 의 `BedrockLlm.summarize_event`, `summarize_case`
- **참고**: `prompts/timeline.md`, `prompts/summary.md`
- **고정**: 정렬·이벤트 선택은 `worker/services/timeline.py`(규칙). LLM은 문장만 다듬는다.

## 3) 다국어 담당 — 번역·대조표·i18n

- **구현할 것**: `worker/providers/translate.py` 의 `AmazonTranslator.translate`
- **프론트 i18n**: `backend/app/static/index.html` 의 `T` 사전(ko/vi/en) 확장, km/ne/id 추가
- **고정**: 원문은 항상 보존. 대조표 조립은 `worker/services/translation.py`.
- **주의**: 크메르/네팔은 ko→en→km 피벗 고려(tech.md).

## 4) 인증 담당 — 로그인

- **구현된 것**: 소셜 OAuth(`/auth/{provider}/login`·`/callback`, `auth_service.py`) + 자체 HS256 JWT 발급/검증, `bada://auth` 딥링크 토큰 반환
- **전환**: `AUTH_MODE=oauth` (Cognito Hosted UI는 미사용 레거시 — `data.tf` 리소스만 잔존)
- **고정**: 라우터는 이미 `Depends(get_current_user)` 사용 → 라우터 수정 불필요.

## 5) 스토리지/인프라 담당 — 파일·배포

- **구현할 것**: `backend/app/services/storage.py:S3Storage` (이미 골격), `infra/*.tf` (RDS+PostGIS·S3·SQS(+DLQ)·Cognito·ECR·ALB·Fargate)
- **참고**: `docs/infra/implementation-status.md`
- **전환**: `STORAGE_MODE=s3`, `DATABASE_URL`을 Postgres로.
- **운영 기준**:
  - `ALB public subnet / ECS·RDS private subnet` (3-tier, 2026-07-03 적용)
  - `단일 NAT Gateway egress + S3 Gateway Endpoint(무료)` (토글: nat_gateway_enabled + ecs_in_private_subnets)
  - `RDS Multi-AZ (encrypted, cutover 완료 — 원본 Single-AZ는 rollback 보존)`
  - `Secrets Manager + SSM Parameter Store 분리`
  - `CloudWatch Logs/Alarms`, 짧은 로그 보존기간

## 6) GPS 담당 — 지오펜스·수집

- **구현할 것**: 프론트 웹 Geolocation ping 전송(`/cases/{id}/gps/ping` 사용), 시드 로그 확장
- **고정**: 판정·교차검증은 `worker/rules/geofence.py`(규칙, 테스트됨). `is_mocked` 배제 로직 유지.
- **확장(스트레치)**: 네이티브 앱 백그라운드 추적.

## 7) 프론트/PM 담당 — 화면·데모·평가셋

- **화면**: `backend/app/static/index.html` (화면 추가/개선)
- **평가셋**: `eval/dataset/` 라벨링(20~30건) → `python eval/harness.py` 로 정확도 측정
- **데모/발표**: `seed.py` 데이터, 시나리오

## API 계약 (프론트-백엔드 공유, 고정)

```
POST /cases                         사건 생성
GET  /cases, /cases/{id}            목록/상세
POST /cases/{id}/evidences/manual   분류만 등록
POST /cases/{id}/evidences/upload   파일 업로드(multipart: category,file)
POST /cases/{id}/analyze?lang=ko    분석 실행(결과 반환)
GET  /cases/{id}/analysis           결과 재조회
GET  /cases/{id}/timeline           타임라인
GET  /cases/{id}/translation-pairs  원문-번역 대조표
GET  /cases/{id}/missing            누락 체크리스트
GET  /cases/{id}/report.html        제출용 리포트
POST /cases/{id}/gps/ping           GPS 핑 수신
```
