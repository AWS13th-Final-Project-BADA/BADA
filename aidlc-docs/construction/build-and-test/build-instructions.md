# 빌드 지침서

## 사전 조건

- AWS CLI 설정 완료 (ap-northeast-2)
- Terraform 1.x 설치
- Docker 설치
- Node.js 20+ 설치
- Python 3.11 설치

---

## 1단계: Terraform 인프라 배포

```bash
cd infra

# terraform.tfvars 업데이트
# domain_name = "badasoft.com"
# frontend_enabled = false   (유닛 5 배포 전까지)
# worker_desired_count = 1
# backend_provider_mode = "aws"
# backend_ai_chat_mode = "bedrock"
# worker_provider_mode = "aws"
# cognito_callback_urls = ["https://api.badasoft.com/auth/cognito/callback", "http://localhost:8000/auth/cognito/callback"]
# cognito_logout_urls = ["https://badasoft.com/", "http://localhost:8000/"]

terraform init
terraform plan
terraform apply
```

**확인 항목:**
- [ ] ACM 인증서 발급 (DNS 검증 완료)
- [ ] ALB HTTPS listener(443) 동작
- [ ] Route 53 A 레코드 (badasoft.com, api.badasoft.com)
- [ ] Worker ECS Service desired=1, running=1
- [ ] ALB access log S3 버킷 생성

---

## 2단계: Backend 빌드 및 배포

```bash
cd backend

# 로컬 테스트
pip install -r requirements.txt
pytest -q

# Docker 빌드 (GitHub Actions가 자동 수행)
docker build -f Dockerfile -t bada-backend .

# 수동 배포 시
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <ECR_URI>
docker tag bada-backend:latest <ECR_URI>/bada-dev-backend:latest
docker push <ECR_URI>/bada-dev-backend:latest
aws ecs update-service --cluster bada-dev-cluster --service bada-dev-backend --force-new-deployment
```

**확인 항목:**
- [ ] `https://api.badasoft.com/health` → `{"status":"ok"}`
- [ ] `https://api.badasoft.com/version` → `auth_mode: "cognito"`
- [ ] 보안 헤더 응답 확인 (X-Content-Type-Options, HSTS 등)
- [ ] CORS: `https://badasoft.com` 허용, 기타 거부

---

## 3단계: Worker 빌드 및 배포

```bash
# Docker 빌드 (GitHub Actions가 자동 수행)
docker build -f worker/Dockerfile -t bada-worker .

# 수동 배포 시
docker tag bada-worker:latest <ECR_URI>/bada-dev-worker:latest
docker push <ECR_URI>/bada-dev-worker:latest
aws ecs update-service --cluster bada-dev-cluster --service bada-dev-worker --force-new-deployment
```

**확인 항목:**
- [ ] Worker ECS Task running (CloudWatch Logs에 "consumer 시작" 로그)
- [ ] SQS 메시지 수신 테스트 (수동 메시지 전송 → 처리 확인)

---

## 4단계: Frontend 빌드 및 배포

```bash
cd frontend

# 로컬 개발
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev

# 프로덕션 빌드
NEXT_PUBLIC_API_URL=https://api.badasoft.com npm run build

# Docker 빌드
docker build -f Dockerfile -t bada-frontend .

# ECR 푸시 + ECS 배포
# (terraform에서 frontend_enabled = true 후 apply 필요)
docker tag bada-frontend:latest <ECR_URI>/bada-dev-frontend:latest
docker push <ECR_URI>/bada-dev-frontend:latest
aws ecs update-service --cluster bada-dev-cluster --service bada-dev-frontend --force-new-deployment
```

**확인 항목:**
- [ ] `https://badasoft.com` 접속 → 로그인 화면
- [ ] Cognito 로그인 → 사건 목록 화면

---

## 5단계: Terraform Frontend 활성화

```bash
cd infra
# terraform.tfvars: frontend_enabled = true
terraform apply
```

이후 Frontend ECS Service가 생성되고 ALB 호스트 라우팅 활성화.
