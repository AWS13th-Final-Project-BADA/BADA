# AWS 셋업 체크리스트 (Infra/DevOps — 반나절)

> 코딩이 아니라 환경 설정 작업. W1 시작 전에 끝내두면 막힘이 없다.
> 운영 기준: `2026-06-04 ~ 2026-07-10`, 팀 전체 AWS 총 예산 `1,500달러`

## 계정·권한
- [ ] 팀 공용 AWS 계정/조직 확인, IAM 사용자·역할 생성 (최소권한)
- [ ] 리전 고정: **ap-northeast-2 (서울)**
- [ ] 비용 알람: Budgets로 월 한도 + 80% 알림 (CloudWatch)
- [ ] 예산 운영 원칙 공유: AI 비용도 포함한 총액 1,500달러 기준, 인프라는 `NAT Gateway 미사용`, `RDS Single-AZ`, `Fargate 최소 안정 사양`

## Bedrock (가장 자주 빠뜨림)
- [ ] 콘솔 → Bedrock → **Model access**에서 Claude 모델 활성화 신청/승인
- [ ] 사용할 모델 ID 확정 후 `.env`의 `BEDROCK_MODEL_ID` 갱신
- [ ] Vision 호출 리전이 모델 지원 리전인지 확인

## Upstage (외부 API)
- [ ] Document Parse API 키 발급 → `.env` `UPSTAGE_API_KEY`
- [ ] ⚠️ 전송 전 PII 마스킹 적용 확인 (security.md)

## 데이터/스토리지
- [ ] Terraform 초기화: `cd infra && terraform init`
- [ ] S3 버킷(KMS 암호화, 퍼블릭 차단) — Terraform으로 생성
- [ ] RDS PostgreSQL 생성 후 `CREATE EXTENSION postgis;`
- [ ] SQS 큐 생성, URL을 `.env` `SQS_QUEUE_URL`
- [ ] SQS DLQ 생성 여부 확인
- [ ] ECR 리포지토리 생성 (backend / worker)

## 인증
- [ ] Cognito User Pool + App Client 생성 → `.env` 갱신

## 네트워크 / 배포
- [ ] VPC / subnet 전략 확정: `ALB/ECS public`, `RDS private`
- [ ] NAT Gateway는 생성하지 않음
- [ ] ALB 생성 및 ECS backend service 연결
- [ ] ECS backend / worker task 사양은 최소 안정 사양부터 시작
- [ ] RDS는 Single-AZ로 시작하고 Multi-AZ는 적용하지 않음

## 리포/CI
- [ ] 모노레포 git 초기화, 브랜치 전략(main + feature)
- [ ] 비밀키는 SSM/Secrets Manager (코드/`.env` 커밋 금지 — .gitignore 확인)
- [ ] 민감정보는 Secrets Manager, 비민감 설정은 SSM Parameter Store로 분리
- [ ] CloudWatch 로그 보존기간은 7일 또는 14일로 설정

## 폰트 (PDF — W3 전에)
- [ ] Noto Sans KR / Khmer / Devanagari .ttf 확보 → worker 컨테이너에 임베딩
- [ ] 크메르·데바나가리 1장 렌더 육안 검증
