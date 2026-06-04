# BADA

외국인·취약 노동자가 흩어진 증거를 올리면, AI가 OCR·번역으로 사실관계를 구조화하여
**사건 타임라인 + 미지급 의심 금액 + 상담/신고 제출용 Evidence Pack(PDF)** 을 만들고,
다음 행동을 모국어로 안내하는 도구.

> ⚖️ BADA는 법률자문이 아니라 **상담 준비용 증거 정리 도구**입니다.
> 위법·체불 여부, 받을 금액을 확정하지 않습니다.

## 설계 원칙 (한 줄)

**계산·비교·정렬·판정은 규칙 기반 코드. 문장화·요약·OCR만 LLM.**
→ "AI가 금액을 잘못 계산하면?"에 "계산은 AI가 안 한다"고 답할 수 있다.

## 리포 구조

```
backend/   FastAPI API 서버
worker/    분석 워커 (rules = 규칙엔진, llm = OCR·문장화)
prompts/   LLM 프롬프트 템플릿
frontend/  Next.js + next-intl (다국어)
infra/     Terraform (AWS IaC)
eval/      평가셋 + 정확도 측정
docs/      체크리스트·문서
.kiro/steering/  AI-DLC 규칙 (AI가 항상 참조)
```
자세한 규칙은 `.kiro/steering/` 참조.

## 빠른 시작 (로컬)

```bash
# 1) DB (postgres + postgis)
docker compose up -d

# 2) 백엔드
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# 3) 규칙 엔진 테스트 (LLM/AWS 없이 동작)
cd worker && pip install -r requirements.txt && pytest -q
```

## 스택 (AWS 관리형 단일 노선)

ECR · ECS Fargate · ALB · RDS PostgreSQL+PostGIS · S3+KMS · SQS(+DLQ) · Cognito ·
Secrets Manager · SSM Parameter Store · CloudWatch Logs/Alarms ·
Bedrock(Claude) · Amazon Translate · WeasyPrint.
금지: K8s, Kafka, OpenAI, Textract, ReportLab (이유는 `.kiro/steering/tech.md`).

## 인프라 운영 기준

- 프로젝트 운영 기간: `2026-06-04` ~ `2026-07-10`
- 팀 전체 AWS 총 예산: `1,500달러`
- 원칙: AI(Bedrock/OCR/번역) 비용도 함께 고려하되, 인프라는 지나치게 축소하지 않고 안정적인 데모가 가능한 수준으로 구성
- 네트워크 기본 원칙: `ALB/ECS는 public subnet`, `RDS는 private subnet`, `NAT Gateway는 사용하지 않음`
- 비용 통제 원칙: `RDS Single-AZ`, `Fargate 최소 안정 사양`, `CloudWatch 로그 보존기간 단축`, `Secrets 최소화 + 비민감 값은 SSM 분리`

## 5주 로드맵 / bolt

`docs/roadmap.md` (작성 예정) 참조. 매 주말 게이트 통과 여부로 컷을 결정한다.
사람이 반드시 검증할 게이트: 평가셋 라벨링, OCR 정확도, 다국어 폰트 렌더, 표현 톤, GPS 교차검증.
