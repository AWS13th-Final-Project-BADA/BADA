---
inclusion: always
---

# BADA — 기술 스택 제약 (Tech Steering)

> 코드·인프라·의존성을 생성할 때 이 제약을 지킨다.
> "금지" 목록의 기술을 제안하거나 추가하지 말 것. 요청이 있어도 대안(허용 스택)으로 안내한다.
> 원칙: **5주 MVP는 AWS 관리형 단일 노선으로만 간다.**

## 1. 허용 스택 (이것만 사용)

### 인프라 (AWS 관리형)
- 컨테이너 이미지: **ECR**
- 컴퓨트: **ECS Fargate** (Backend API + Worker 컨테이너)
- API 진입점: **ALB**
- DB: **RDS PostgreSQL + PostGIS 확장** (사용자/사건/분석결과 + GPS 공간연산)
- 스토리지: **S3 + KMS 암호화** (원본 증거 + 생성 PDF)
- 큐: **SQS + DLQ** (분석 작업 비동기 — 단일 워커가 단계 순차 실행)
- 인증: **Cognito** (이메일 로그인)
- 시크릿: **Secrets Manager** (민감정보), **SSM Parameter Store** (비민감 설정)
- LLM: **Amazon Bedrock (Claude)** — OCR, 문장화, 요약
- 번역: **Amazon Translate**
- 로깅: **CloudWatch Logs + Alarms**
- IaC: **Terraform**

### 백엔드 / 프론트
- 백엔드: **FastAPI (Python)** — 비동기, Bedrock/규칙로직 연동
- 프론트: **Next.js (App Router) + Tailwind**
- i18n: **next-intl** (정적 UI 텍스트, JSON locale)
- 데이터 검증: **Pydantic** (LLM 출력 스키마 강제)
- PDF: **WeasyPrint** (HTML/CSS 템플릿 → PDF) + **Noto Sans** 폰트 패밀리

### OCR (2-엔진 라우팅)
- 비정형 (카톡 캡처, 통장 앱 스크린샷, 사진, 손메모): **Bedrock Claude Vision**
- 정형 (급여명세서, 계약서, 근무표, PDF 거래내역): **Upstage Document Parse**

## 2. 금지 스택 (제안·추가 금지)

| 금지 | 이유 | 대안 |
| --- | --- | --- |
| Kubernetes / K8s / HPA | 5주에 클러스터 운영 불가 | ECS Fargate |
| Kafka | 데모 트래픽 스파이크 없음 | SQS |
| NAT Gateway | 현재 기간/예산 대비 고정비 부담이 큼 | ECS public subnet + RDS private subnet |
| Step Functions | W1 부담 | 단일 워커 순차 실행 (MVP) |
| OpenSearch | 본격 RAG는 Phase 2 | (MVP) 정적 FAQ / pgvector는 Phase 2 |
| **OpenAI / 외부 LLM API** | 스택은 Bedrock(AWS 신뢰경계). 외부 직배송 안 함 | Bedrock Claude |
| **ReportLab** | 다국어 합자 렌더링 취약 | WeasyPrint |
| Amazon Textract | **한국어 미지원** (입력 문서가 전부 한국어) | Claude Vision / Upstage |
| 자체 번역 모델 학습 | 5주에 불가 | Amazon Translate (+ Claude 보정) |

## 3. OCR 라우팅 규칙 (카테고리 기반 — MVP 채택)

언어로 가르지 않는다. **"문서냐 이미지냐"** 형태로만 판단한다.

```
사용자가 업로드 + 카테고리 선택
  │
  ├─ 명세서·계약서·근무표 → Upstage
  ├─ 카톡·메모          → Claude Vision
  ├─ 통장: PDF 내역서 → Upstage / 앱 캡처 → Claude Vision
  └─ 애매하거나 섞이면 → Claude Vision (안전 기본값)
```
- 근거: 사용자가 직접 분류하므로 추측이 없다. 애매하면 멀티모달인 Claude가 일단 읽기 가능.
- 자동 판별 분기는 **Phase 2** (MVP는 사용자 카테고리 선택까지만).

## 4. PDF 다국어 렌더링 (반드시 지킬 것)

WeasyPrint 컨테이너(Dockerfile)에 폰트를 임베딩한다. 누락 시 ▯▯▯ 깨짐.
```dockerfile
RUN apt-get install -y fonts-noto-cjk fonts-noto-color-emoji
COPY fonts/NotoSansKhmer.ttf /usr/share/fonts/
COPY fonts/NotoSansDevanagari.ttf /usr/share/fonts/
RUN fc-cache -fv
```
CSS는 `:lang()` 으로 폰트 자동 분기:
```css
:lang(ko) { font-family: 'Noto Sans KR', sans-serif; }
:lang(km) { font-family: 'Noto Sans Khmer', sans-serif; }   /* 크메르어 */
:lang(ne) { font-family: 'Noto Sans Devanagari', sans-serif; } /* 네팔어 — 합자 주의 */
```
- ⚠️ **W3 첫날에 크메르·데바나가리 1장 렌더 육안 검증**을 게이트로 둔다.

## 5. 번역 전략

- 베트남어·인도네시아어·영어 → Amazon Translate 단독으로 충분.
- 크메르어·네팔어 → Translate 초벌 + Claude 보정, 또는 ko→en→km 영어 피벗.
- **원문-번역 대조표는 항상 원문 병기** (번역 오류 시 원문 확인 가능하게).
- 데모 언어는 우선 **베트남어 + 영어 2개**만 완성도 확보, 나머지는 i18n 골격만.

## 6. PDF는 2종 → MVP는 1종 + 화면

- 제출용 PDF: **한국어 고정** (공식 행정문서).
- 이해용: MVP에서는 별도 PDF 대신 **모국어 결과 화면**으로 대체 (W3 부하 감소).

## 7. 인프라 운영 원칙

- 프로젝트 운영 기간: `2026-06-04` ~ `2026-07-10`
- 팀 전체 AWS 총 예산: `1,500달러`
- 인프라는 AI(Bedrock/OCR/번역) 비용을 고려해 구성하되, 데모 안정성을 해치지 않는 수준의 관리형 서비스를 사용한다
- RDS는 `Single-AZ`로 시작한다
- ECS Fargate는 `backend 1 task`, `worker 1 task`의 최소 안정 사양부터 시작한다
- CloudWatch 로그 보존기간은 짧게 가져가고, 민감정보와 비민감 설정은 분리 저장한다
