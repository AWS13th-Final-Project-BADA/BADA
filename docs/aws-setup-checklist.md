# AWS 셋업 체크리스트 (Infra/DevOps — 반나절)

> 코딩이 아니라 환경 설정 작업. W1 시작 전에 끝내두면 막힘이 없다.

## 계정·권한
- [ ] 팀 공용 AWS 계정/조직 확인, IAM 사용자·역할 생성 (최소권한)
- [ ] 리전 고정: **ap-northeast-2 (서울)**
- [ ] 비용 알람: Budgets로 월 한도 + 80% 알림 (CloudWatch)

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

## 인증
- [ ] Cognito User Pool + App Client 생성 → `.env` 갱신

## 리포/CI
- [ ] 모노레포 git 초기화, 브랜치 전략(main + feature)
- [ ] 비밀키는 SSM/Secrets Manager (코드/`.env` 커밋 금지 — .gitignore 확인)

## 폰트 (PDF — W3 전에)
- [ ] Noto Sans KR / Khmer / Devanagari .ttf 확보 → worker 컨테이너에 임베딩
- [ ] 크메르·데바나가리 1장 렌더 육안 검증
