# BADA 분산 k6 Runner (ECS Fargate)

단일 로컬 k6는 **하나의 source IP**라 앱 IP rate limit(IP당 300건/60초, 429)에 먼저 걸려 비면제 엔드포인트의 실제 인프라 한계를 측정할 수 없다. 이 runner는 **여러 Fargate 태스크를 각기 다른 public IP로 띄워** 단일 소스 IP 한계를 제거하고 **실제 다수 사용자 분산 접속 조건을 재현**한다. (앱 `rate_limit.py` 정책은 수정·완화하지 않는다. 목표는 우회가 아니라 실사용 조건 재현이다.)

## 구성 (이번 PR: Terraform 없이 CLI + Task Definition JSON)

```text
load-test/k6-runner/
├── Dockerfile              # grafana/k6 + curl + bash + jq + aws-cli (ARM64)
├── entrypoint.sh           # 안전장치 + source IP 기록 + k6 실행 + 결과 S3 업로드
├── task-definition.json    # ECS Task Definition 템플릿(setup-infra.sh가 채워 등록)
├── scripts/
│   ├── distributed-http.js # 비면제 엔드포인트 부하 + status(429/5xx) 분포 집계
│   └── source-ip-check.sh  # external source IP 확인기(checkip → ipify 폴백)
└── run/
    ├── setup-infra.sh          # ECR/LogGroup/S3/IAM/SG 생성 + TaskDef 등록(AWS CLI) → runner-env.sh 산출
    ├── build-and-push.sh       # docker buildx(arm64) → ECR push
    ├── run-distributed-k6.sh   # RunTask N개(public IP) 오케스트레이션 + 안전 재검사
    ├── collect-results.sh      # 결과 S3 수집 + distinct source IP 검증
    └── stop-runners.sh         # 실행 중 runner 태스크 stop
```

> **Terraform 기반 관리는 별도 PR 후보다.** 이번 PR은 범위를 `load-test/**`로 제한하기 위해 Terraform 리소스를 추가하지 않고 AWS CLI + Task Definition JSON으로 최소 구현한다. runner 리소스를 IaC로 관리하려면 별도 독립 state(perf 전용)로 ECR/LogGroup/IAM/SG/TaskDef/S3를 정의하는 Terraform PR을 뒤이어 올린다.

## 안전 원칙 (강제)
- **대상은 perf ALB HTTP만** — `entrypoint.sh`와 `run/run-distributed-k6.sh` 양쪽에서 `badasoft.com`/dev/prod URL이면 즉시 종료. `http://bada-perf-*` 패턴만 허용.
- dev/prod state·리소스 미변경. runner 리소스는 모두 `bada-perf-*` 이름의 독립 리소스로 만든다.
- rate limit 정책 제거·완화 금지. 목표는 우회가 아니라 **source IP 분산으로 실사용 조건 재현**.
- **source IP 분산 검증(collect-results.sh)이 통과하기 전에는 5,000 VU 이상 실행 금지.** 분산이 안 되면 429만 쌓여 rate limit 테스트가 되어 버린다.
- 테스트 후 runner 태스크 + perf 리소스 전부 정리(destroy/stop).

---

## 실행 런북

### Phase 1 — perf 환경 재기립 (인프라 담당 수행)
```bash
cd infra
terraform init -reconfigure -backend-config=backends/perf.hcl
terraform plan  -var-file=env/perf.tfvars      # bada-perf-* 생성만, dev/prod 변경 0 확인
terraform apply -var-file=env/perf.tfvars      # apply
terraform output alb_dns_name                  # → export TARGET_URL=http://<alb_dns>
```
smoke: `curl -fsS http://<perf-alb-dns>/health` → 200

### Phase 2 — runner 인프라 셋업 + 이미지 push
```bash
cd load-test/k6-runner/run
ACCOUNT_ID=<ACCOUNT_ID> VPC_ID=<perf-vpc-id> \
  SUBNETS="<perf-public-subnet-a>,<perf-public-subnet-b>" \
  CLUSTER="bada-perf-cluster" \
  ./setup-infra.sh          # ECR/LogGroup/S3/IAM/SG 생성 + TaskDef 등록 → runner-env.sh 생성
./build-and-push.sh         # arm64 이미지 빌드 후 ECR push
```
`runner-env.sh`(git 미추적)에 CLUSTER/SUBNETS/SECURITY_GROUP/TASKDEF/RESULT_S3_BUCKET 등이 기록되어 이후 스크립트가 자동 로드한다.

### Phase 3 — source IP 분산 검증 (5k~10k 전 필수)
작은 부하로 runner 5개를 띄워 external IP가 실제로 분산되는지 먼저 확인한다.
```bash
export TARGET_URL="http://<perf-alb-dns>"     # 안전장치가 perf 패턴만 허용
RUNNERS=5 VUS_PER_RUNNER=10 DURATION=30s ./run-distributed-k6.sh
# 태스크 종료 후 결과 수집 + distinct IP 판정
./collect-results.sh
```
- distinct external IP 수가 runner 수(5)에 근접 → **PASS** → Phase 4 진행
- 모두 같은 IP → **FAIL** → public subnet/assignPublicIp 설정 재확인(단일 NAT 뒤면 안 됨)

### Phase 4 — 단계별 부하 (5,000 → 7,500 → 10,000 VU 상당)
```bash
RUNNERS=10 VUS_PER_RUNNER=500 DURATION=8m ./run-distributed-k6.sh   # 5,000 VU 상당
RUNNERS=15 VUS_PER_RUNNER=500 DURATION=8m ./run-distributed-k6.sh   # 7,500
RUNNERS=20 VUS_PER_RUNNER=500 DURATION=8m ./run-distributed-k6.sh   # 10,000
```
각 단계 사이 cooldown. 수집: `collect-results.sh`의 k6 summary + CloudWatch(ALB 2XX/4XX/5XX·TargetResponseTime, ECS RunningTaskCount·CPU, RDS CPU·Connections, SQS).

**중단 기준**: 5xx 급증(서버 실오류), p95 과도 상승·회복 불가, 비용 급증, 계정 상한 접근.

### Phase 5 — SQS 대량 backlog (선택, HTTP와 별개)
```bash
python ../../sqs/fill_backlog.py --queue bada-perf-analysis --count 100000 --workers 80 --watch --profile bada-team
```
Worker scale-out·drain·DLQ 관측. **queue는 bada-perf-* 만.**

### Phase 6 — 정리 / cleanup
```bash
cd load-test/k6-runner/run
./stop-runners.sh           # 실행 중 runner 태스크 stop
# runner 리소스 정리(CLI로 만든 것): TaskDef deregister, S3/ECR/IAM/SG/LogGroup 삭제
# perf 환경 destroy는 인프라 담당이 수행:
cd ../../../infra
terraform init -reconfigure -backend-config=backends/perf.hcl
terraform destroy -var-file=env/perf.tfvars
terraform init -reconfigure -backend-config=backends/dev.hcl
terraform plan     # → No changes
```

## 수집·기록 지표
- k6: RPS, p95/p99, error rate, **status 분포(429 vs 5xx)**
- ALB: RequestCount, TargetResponseTime, 2XX/4XX/5XX
- ECS Backend: RunningTaskCount(scale-out), CPU/Mem
- RDS: CPU, DatabaseConnections
- SQS: visible/in-flight/oldest age, DLQ
- 결과는 `load-test/perf-scale-experiment.md`와 `load-test/performance-case-study.md`에 정리

> ⚠️ 본 문서는 실행 절차서다. 실제 `terraform apply`/`docker push`/`run-task`/`destroy`는 인프라 담당이 비용·쿼터·중단기준을 확인하며 수행한다.
