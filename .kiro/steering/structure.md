---
inclusion: always
---

# BADA — 코드 구조 (Structure Steering)

> 파일·폴더·모듈을 생성할 때 이 레이아웃과 네이밍을 따른다.
> 새 코드는 정해진 위치에만 둔다. 규칙 로직과 LLM 로직은 디렉토리로 분리한다(architecture.md).

## 1. 모노레포 레이아웃

```
BADA/
├─ .kiro/steering/        # AI-DLC steering 규칙 (이 디렉토리)
├─ backend/               # FastAPI API 서버 (ECS Fargate)
│  ├─ app/
│  │  ├─ main.py          # FastAPI 엔트리
│  │  ├─ config.py        # 환경설정 (pydantic-settings)
│  │  ├─ db.py            # SQLAlchemy 세션
│  │  ├─ models/          # SQLAlchemy ORM (DB 테이블)
│  │  ├─ schemas/         # Pydantic (요청/응답 + LLM 출력 스키마)
│  │  ├─ routers/         # API 엔드포인트
│  │  └─ services/        # S3 presigned, SQS 전송 등
│  ├─ tests/
│  └─ requirements.txt
├─ worker/                # 분석 워커 (ECS Fargate, SQS 소비)
│  ├─ pipeline.py         # 8단계 순차 오케스트레이션
│  ├─ rules/              # ★ 규칙 기반 로직 (생성형 금지)
│  │  ├─ wage.py          # 급여-입금 차액
│  │  ├─ deductions.py    # 공제 분류 + 사전
│  │  ├─ missing.py       # 누락 체크리스트
│  │  └─ geofence.py      # GPS 지오펜스 + 교차검증
│  ├─ llm/                # ★ LLM 로직 (OCR·문장화만)
│  │  ├─ bedrock.py       # Claude Vision/Text 클라이언트
│  │  ├─ upstage.py       # Upstage (PII 마스킹 후 호출)
│  │  └─ prompts.py       # /prompts 로더
│  ├─ security/pii.py     # 정규식 마스킹
│  ├─ pdf/                # WeasyPrint 렌더 + HTML 템플릿
│  ├─ tests/
│  └─ requirements.txt
├─ prompts/               # LLM 프롬프트 템플릿 (버전 관리 대상)
│  ├─ extraction.md
│  ├─ classification.md
│  ├─ timeline.md
│  └─ summary.md
├─ frontend/              # Next.js (App Router) + next-intl
│  ├─ app/
│  ├─ components/
│  ├─ locales/            # ko/vi/km/ne/id/en.json
│  └─ lib/
├─ infra/                 # Terraform (AWS IaC)
│  ├─ main.tf             # 핵심 리소스 (VPC/ALB/ECS/RDS/S3/SQS/Cognito 등)
│  ├─ providers.tf        # provider 설정
│  ├─ variables.tf        # 입력 변수
│  ├─ outputs.tf          # 출력값
│  ├─ github-actions.tf   # OIDC 배포 Role / 권한
│  ├─ terraform.tfvars.example  # tfvars 템플릿 (실제 tfvars는 Git 비추적)
│  └─ README.md           # Terraform 실행 방법 / 인프라 코드 구조
├─ eval/                  # 평가셋 + 정확도 측정 하네스
│  ├─ dataset/            # 라벨된 샘플 (gold)
│  └─ harness.py
├─ docs/                  # 체크리스트·설계 문서
└─ docker-compose.yml     # 로컬 개발 (postgres+postgis)
```

## 2. 네이밍 규칙

- 파이썬: 모듈·함수 `snake_case`, 클래스 `PascalCase`.
- DB 컬럼: `snake_case` (domain.md 스키마와 일치).
- enum 값: 소문자 문자열 (`wage_unpaid`, `IN_WORKPLACE`는 GPS status만 대문자 — domain.md 따름).
- API 경로: 복수형 리소스 (`/cases/{id}/evidences`).
- 프론트 컴포넌트: `PascalCase.tsx`. locale 키: `snake_case`.

## 3. 분리 원칙 (디렉토리로 강제)

- `worker/rules/**` 안에서는 **Bedrock/LLM 호출 금지**. 순수 함수 + 단위테스트 가능해야 한다.
- `worker/llm/**` 는 텍스트 입출력만. 계산·판정 결과를 만들지 않는다.
- 두 디렉토리를 섞지 말 것 — 이게 "계산은 규칙, 문장화는 LLM" 불변식의 물리적 경계다.

## 4. 테스트

- 규칙 엔진(`worker/rules/**`)은 **단위테스트 필수** (계산이 설명 가능해야 하므로).
- LLM 모듈은 스키마 검증·재시도 로직 위주로 테스트, 실제 호출은 모킹.
- `eval/harness.py`는 gold dataset 대비 OCR/차액/누락 정확도를 출력한다.

## 5. 환경/비밀

- 비밀키는 코드에 두지 않는다 (`.env`는 gitignore, 운영은 SSM/Secrets Manager).
- 로컬은 `docker-compose`로 postgres+postgis 띄워 개발.
