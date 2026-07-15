#!/usr/bin/env bash
# BADA 분산 k6 runner — 최소 인프라 셋업 (AWS CLI, perf 전용)
# 목적: 이 PR은 Terraform 변경 없이 CLI로 runner 실행에 필요한 최소 리소스만 만든다.
#       (ECR repo, CloudWatch Log Group, S3 결과 버킷, IAM exec/task role, egress-only SG,
#        ECS Task Definition 등록) → 산출물을 runner-env.sh로 남겨 다른 스크립트가 source 한다.
#
# ⚠️ Terraform 기반 관리는 별도 PR 후보다(README '별도 PR 후보' 절 참고). 여기서는 dev/prod
#    state·리소스를 건드리지 않고 bada-perf-* 이름의 독립 리소스만 생성한다.
#
# 필수 환경변수:
#   ACCOUNT_ID   AWS 계정 ID (S3 버킷 이름 유일화)
#   VPC_ID       runner를 둘 perf VPC (SG 생성 대상). ALB는 public이라 인터넷 경유 호출.
#   SUBNETS      perf public subnet ID 쉼표구분 (run 단계에서 사용, runner-env.sh에 기록)
#   CLUSTER      perf ECS 클러스터 (예: bada-perf-cluster)
# 선택:
#   AWS_REGION(기본 ap-northeast-2) AWS_PROFILE(기본 bada-team)
set -euo pipefail

: "${ACCOUNT_ID:?ACCOUNT_ID 필요}"
: "${VPC_ID:?VPC_ID 필요(perf VPC)}"
: "${SUBNETS:?SUBNETS 필요(perf public subnet ids, 쉼표구분)}"
: "${CLUSTER:?CLUSTER 필요(예: bada-perf-cluster)}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
AWS_PROFILE="${AWS_PROFILE:-bada-team}"
NAME="bada-perf-k6-runner"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_DIR="$(cd "$HERE/.." && pwd)"

aws() { command aws --region "$AWS_REGION" --profile "$AWS_PROFILE" "$@"; }
log() { echo "[setup] $*"; }

# ─── 안전 재검사: perf VPC인지 이름 태그로 확인(권장) ──────────────────────
VPC_NAME="$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" \
  --query "Vpcs[0].Tags[?Key=='Name']|[0].Value" --output text 2>/dev/null || echo "")"
case "$VPC_NAME" in
  *perf*) log "perf VPC 확인: $VPC_ID ($VPC_NAME)" ;;
  *) echo "[setup][WARN] VPC 이름에 'perf'가 없음: '$VPC_NAME'. dev/prod VPC가 아닌지 반드시 확인하세요." >&2 ;;
esac

# ─── ECR ────────────────────────────────────────────────────────────────────
aws ecr describe-repositories --repository-names "$NAME" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$NAME" \
       --image-scanning-configuration scanOnPush=true >/dev/null
ECR_URL="$(aws ecr describe-repositories --repository-names "$NAME" \
  --query "repositories[0].repositoryUri" --output text)"
log "ECR: $ECR_URL"

# ─── CloudWatch Logs ────────────────────────────────────────────────────────
aws logs describe-log-groups --log-group-name-prefix "/ecs/$NAME" \
  --query "logGroups[?logGroupName=='/ecs/$NAME']" --output text | grep -q "/ecs/$NAME" \
  || aws logs create-log-group --log-group-name "/ecs/$NAME"
aws logs put-retention-policy --log-group-name "/ecs/$NAME" --retention-in-days 7 || true
log "LogGroup: /ecs/$NAME"

# ─── S3 결과 버킷 ────────────────────────────────────────────────────────────
BUCKET="${NAME}-results-${ACCOUNT_ID}"
if ! aws s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
  aws s3api create-bucket --bucket "$BUCKET" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
fi
log "S3 결과 버킷: $BUCKET"

# ─── IAM: execution role ────────────────────────────────────────────────────
ASSUME='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam get-role --role-name "${NAME}-exec-role" >/dev/null 2>&1 \
  || aws iam create-role --role-name "${NAME}-exec-role" \
       --assume-role-policy-document "$ASSUME" >/dev/null
aws iam attach-role-policy --role-name "${NAME}-exec-role" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy || true
EXEC_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${NAME}-exec-role"

# ─── IAM: task role (S3 PutObject 최소 권한) ────────────────────────────────
aws iam get-role --role-name "${NAME}-task-role" >/dev/null 2>&1 \
  || aws iam create-role --role-name "${NAME}-task-role" \
       --assume-role-policy-document "$ASSUME" >/dev/null
S3_POLICY="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:PutObject\"],\"Resource\":\"arn:aws:s3:::${BUCKET}/*\"}]}"
aws iam put-role-policy --role-name "${NAME}-task-role" \
  --policy-name "${NAME}-s3-put" --policy-document "$S3_POLICY"
TASK_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${NAME}-task-role"
log "IAM roles: exec/task 준비 완료"

# ─── Security Group: egress only ────────────────────────────────────────────
SG_ID="$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${NAME}-sg" "Name=vpc-id,Values=${VPC_ID}" \
  --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || echo "None")"
if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
  SG_ID="$(aws ec2 create-security-group --group-name "${NAME}-sg" \
    --description "k6 runner egress only" --vpc-id "$VPC_ID" \
    --query "GroupId" --output text)"
  # 기본 egress(all)만 사용. inbound 없음.
fi
log "SecurityGroup: $SG_ID (egress only)"

# ─── ECS Task Definition 등록 (task-definition.json 템플릿 채움) ────────────
TMP_TD="$(mktemp)"
sed -e "s|__EXEC_ROLE_ARN__|${EXEC_ROLE_ARN}|g" \
    -e "s|__TASK_ROLE_ARN__|${TASK_ROLE_ARN}|g" \
    -e "s|__IMAGE_URI__|${ECR_URL}:latest|g" \
    -e "s|__AWS_REGION__|${AWS_REGION}|g" \
    -e "s|__RESULT_S3_BUCKET__|${BUCKET}|g" \
    "$RUNNER_DIR/task-definition.json" > "$TMP_TD"
aws ecs register-task-definition --cli-input-json "file://$TMP_TD" \
  --query "taskDefinition.taskDefinitionArn" --output text
rm -f "$TMP_TD"
log "TaskDefinition 등록: $NAME"

# ─── runner-env.sh 산출물 ────────────────────────────────────────────────────
cat > "$HERE/runner-env.sh" <<ENV
# 자동 생성됨(setup-infra.sh). run-distributed-k6.sh / collect-results.sh / stop-runners.sh가 source 한다.
export AWS_REGION="$AWS_REGION"
export AWS_PROFILE="$AWS_PROFILE"
export CLUSTER="$CLUSTER"
export SUBNETS="$SUBNETS"
export SECURITY_GROUP="$SG_ID"
export TASKDEF="$NAME"
export ECR_URL="$ECR_URL"
export RESULT_S3_BUCKET="$BUCKET"
# TARGET_URL은 안전상 자동 설정하지 않는다. 실행 직전 export 하세요:
#   export TARGET_URL="http://<perf-alb-dns>"
ENV
log "산출물 기록: $HERE/runner-env.sh (git 미추적 권장)"
echo
echo "다음: 1) build-and-push.sh 로 이미지 push  2) TARGET_URL export  3) run-distributed-k6.sh 실행"
