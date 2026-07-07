# BADA 분산 k6 Runner (ECS Fargate)

단일 로컬 k6는 **하나의 source IP**라 앱 IP rate limit(IP당 300건/60초, 429)에 먼저 걸려 비면제 엔드포인트의 실제 인프라 한계를 측정할 수 없다. 이 runner는 **여러 Fargate 태스크를 각기 다른 public IP로 띄워** 단일 소스 IP 한계를 제거하고 **실제 다수 사용자 분산 접속 조건을 재현**한다. (앱 `rate_limit.py` 정책은 수정·완화하지 않는다.)

## 구성
```
load-test/k6-runner/
├── Dockerfile              # grafana/k6 + curl + aws-cli
├── entrypoint.sh           # 안전장치 + source IP 기록 + k6 실행 + 결과 S3 업로드
├── scripts/
│   └── distributed-http.js # 비면제 엔드포인트 부하 + status(429/5xx) 분포 집계
├── run-distributed.sh      # RunTask N개 오케스트레이션(public IP)
└── terraform/              # ECR, LogGroup, IAM, SG, TaskDef, 결과 S3 (perf 전용)
```

## 안전 원칙 (강제)
- **대상은 perf ALB HTTP만** — `entrypoint.sh`와 `run-distributed.sh` 양쪽에서 `badasoft.com`/dev/prod URL이면 즉시 종료. `http://bada-perf-alb-*` 패턴만 허용.
- dev/prod state·리소스 미변경. runner는 **독립 Terraform state**(perf 전용).
- rate limit 정책 제거·완화 금지. 목표는 우회가 아니라 **source IP 분산으로 실사용 조건 재현**.
- 테스트 후 runner + perf 전부 destroy.

---

## 실행 런북

### Phase 1 — perf 환경 재기립 (E 수행)
```bash
cd infra
terraform init -reconfigure -backend-config=backends/perf.hcl
terraform plan  -var-file=env/perf.tfvars      # bada-perf-* 생성만, dev/prod 변경 0 확인
terraform apply -var-file=env/perf.tfvars      # E가 apply
terraform output alb_dns_name                  # → TARGET_URL=http://<alb_dns>
```
smoke: `curl -fsS http://<perf-alb-dns>/health` → 200

### Phase 2 — runner 이미지 빌드·push
```bash
cd load-test/k6-runner/terraform
terraform init
terraform apply -var account_id=<ACCOUNT_ID> -var vpc_id=<perf-vpc-id>   # ECR/LogGroup/IAM/SG/TaskDef 생성
ECR=$(terraform output -raw ecr_repository_url)

cd ..                                   # load-test/k6-runner
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin "${ECR%/*}"
docker buildx build --platform linux/arm64 -t "$ECR:latest" --push .
```

### Phase 3 — source IP 분산 검증 (5k~10k 전 필수)
작은 부하로 runner 5개를 띄워 external IP가 실제로 분산되는지 먼저 확인한다.
```bash
export TARGET_URL="http://<perf-alb-dns>"
export CLUSTER="bada-perf-cluster"
export SUBNETS="<perf-public-subnet-a>,<perf-public-subnet-b>"
export SECURITY_GROUP="$(cd terraform && terraform output -raw security_group_id)"
export TASKDEF="bada-perf-k6-runner"
RUNNERS=5 VUS_PER_RUNNER=10 DURATION=30s ./run-distributed.sh
```
검증:
```bash
# 결과 S3에서 source IP 수집 후 distinct count
aws s3 cp "s3://$(cd terraform && terraform output -raw results_bucket)/source-ips/" ./srcips --recursive
cat srcips/*.json | grep -o '"source_ip":"[^"]*"' | sort -u
```
- distinct IP 수가 runner 수(5)에 근접 → **통과** → Phase 4 진행
- 모두 같은 IP → **실패** → public subnet/assignPublicIp 설정 재확인(단일 NAT 뒤면 안 됨)

### Phase 4 — 단계별 부하 (5,000 → 7,500 → 10,000 VU 상당)
```bash
# 5,000 VU 상당
RUNNERS=10 VUS_PER_RUNNER=500 DURATION=8m ./run-distributed.sh
# 7,500
RUNNERS=15 VUS_PER_RUNNER=500 DURATION=8m ./run-distributed.sh
# 10,000
RUNNERS=20 VUS_PER_RUNNER=500 DURATION=8m ./run-distributed.sh
```
각 단계 사이 cooldown. 수집: k6 summary(S3) + CloudWatch(ALB 2XX/4XX/5XX·TargetResponseTime, ECS RunningTaskCount·CPU, RDS CPU·Connections, SQS).

**중단 기준**: 5xx 급증(서버 실오류), p95 과도 상승·회복 불가, 비용 급증, 계정 상한($1,500) 접근.

### Phase 5 — SQS 대량 backlog (선택, HTTP와 별개)
```bash
python ../sqs/fill_backlog.py --queue bada-perf-analysis --count 100000 --workers 80 --watch
```
Worker scale-out·drain·DLQ 관측. **queue는 bada-perf-* 만.**

### Phase 6 — 정리 / destroy (E 수행)
```bash
# runner 태스크 종료 확인
aws ecs list-tasks --cluster bada-perf-cluster --region ap-northeast-2
# runner 인프라 destroy
cd terraform && terraform destroy -var account_id=<ACCOUNT_ID> -var vpc_id=<perf-vpc-id>
# perf 환경 destroy
cd ../../../infra
terraform init -reconfigure -backend-config=backends/perf.hcl
terraform destroy -var-file=env/perf.tfvars
# dev 복귀 + 무영향 확인
terraform init -reconfigure -backend-config=backends/dev.hcl
terraform plan     # → No changes
```

## 수집·기록 지표
- k6: RPS, p95/p99, error rate, **status 분포(429 vs 5xx)**
- ALB: RequestCount, TargetResponseTime, 2XX/4XX/5XX
- ECS Backend: RunningTaskCount(scale-out), CPU/Mem
- RDS: CPU, DatabaseConnections
- SQS: visible/in-flight/oldest age, DLQ
- 결과는 `docs/infra/load-test/`(개인) 및 필요 시 `load-test/performance-case-study.md`에 정리

> ⚠️ 본 문서는 실행 절차서다. 실제 `terraform apply`/`docker push`/`run-task`/`destroy`는 인프라 담당이 비용·쿼터·중단기준을 확인하며 수행한다.
