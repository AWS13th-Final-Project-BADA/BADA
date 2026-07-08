#!/usr/bin/env bash
# BADA 분산 k6 runner — 실행 중 runner 태스크 중지
# 대상 클러스터에서 이 task def(bada-perf-k6-runner)로 뜬 태스크를 찾아 stop 한다.
# runner-env.sh(CLUSTER/TASKDEF/AWS_REGION/AWS_PROFILE)를 자동 로드한다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$HERE/runner-env.sh" ] && . "$HERE/runner-env.sh"

: "${CLUSTER:?CLUSTER 필요}"
TASKDEF="${TASKDEF:-bada-perf-k6-runner}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
AWS_PROFILE="${AWS_PROFILE:-bada-team}"

aws() { command aws --region "$AWS_REGION" --profile "$AWS_PROFILE" "$@"; }

echo "[stop] $CLUSTER 에서 $TASKDEF 태스크 조회"
TASKS="$(aws ecs list-tasks --cluster "$CLUSTER" --family "$TASKDEF" \
  --query "taskArns" --output text 2>/dev/null || echo "")"

if [ -z "$TASKS" ] || [ "$TASKS" = "None" ]; then
  echo "[stop] 실행 중인 runner 태스크 없음."
  exit 0
fi

for T in $TASKS; do
  echo "[stop] stopping $T"
  aws ecs stop-task --cluster "$CLUSTER" --task "$T" \
    --reason "load-test manual stop" --query "task.taskArn" --output text || true
done
echo "[stop] 완료. (인프라 정리는 README Phase 6/cleanup 절 참고 — ECR/S3/IAM/SG/LogGroup은 별도 삭제)"
