#!/usr/bin/env bash
# BADA 분산 k6 runner 실행 오케스트레이터
# N개의 Fargate runner 태스크를 public subnet + public IP로 RunTask 하여
# 각기 다른 source IP에서 부하를 생성한다. (dev/prod 대상 금지 — 안전 재검사 포함)
#
# 필수 환경변수:
#   TARGET_URL   perf ALB HTTP (예: http://bada-perf-alb-xxxx.ap-northeast-2.elb.amazonaws.com)
#   CLUSTER      ECS 클러스터 (예: bada-perf-cluster)
#   SUBNETS      public subnet ID 쉼표구분 (perf public subnets)
#   SECURITY_GROUP  runner SG (terraform output security_group_id)
#   TASKDEF      runner task def family/arn (예: bada-perf-k6-runner)
# 선택:
#   RUNNERS(기본 5) VUS_PER_RUNNER(기본 500) DURATION(기본 5m)
#   SCENARIO(기본 distributed-http.js) AWS_REGION(기본 ap-northeast-2)
set -euo pipefail

: "${TARGET_URL:?TARGET_URL 필요(perf ALB)}"
: "${CLUSTER:?CLUSTER 필요}"
: "${SUBNETS:?SUBNETS 필요(public subnet ids, 쉼표구분)}"
: "${SECURITY_GROUP:?SECURITY_GROUP 필요}"
: "${TASKDEF:?TASKDEF 필요}"
RUNNERS="${RUNNERS:-5}"
VUS_PER_RUNNER="${VUS_PER_RUNNER:-500}"
DURATION="${DURATION:-5m}"
SCENARIO="${SCENARIO:-distributed-http.js}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"

# ─── 안전 재검사 (오케스트레이터 레벨) ─────────────────────────────────────
case "$TARGET_URL" in
  *badasoft.com*) echo "[FATAL] 운영 도메인 대상 금지: $TARGET_URL" >&2; exit 1 ;;
  http://bada-perf-alb-*|http://bada-perf-*) : ;;
  *) echo "[FATAL] TARGET_URL이 perf ALB 패턴이 아님: $TARGET_URL" >&2; exit 1 ;;
esac

# subnets를 JSON 배열로 변환
SUBNET_JSON=$(echo "$SUBNETS" | awk -F',' '{for(i=1;i<=NF;i++){printf "%s\"%s\"", (i>1?",":""), $i}}')
NETCFG="awsvpcConfiguration={subnets=[$SUBNET_JSON],securityGroups=[\"$SECURITY_GROUP\"],assignPublicIp=ENABLED}"

echo "총 ${RUNNERS}개 runner · runner당 VUS=${VUS_PER_RUNNER} · duration=${DURATION} · target=${TARGET_URL}"
echo "총 부하 규모 ≈ $((RUNNERS * VUS_PER_RUNNER)) VU 상당"

for i in $(seq 1 "$RUNNERS"); do
  RID="r$(printf '%02d' "$i")"
  OVERRIDES=$(cat <<JSON
{"containerOverrides":[{"name":"k6-runner","environment":[
  {"name":"TARGET_URL","value":"$TARGET_URL"},
  {"name":"SCENARIO","value":"$SCENARIO"},
  {"name":"VUS","value":"$VUS_PER_RUNNER"},
  {"name":"DURATION","value":"$DURATION"},
  {"name":"RUNNER_ID","value":"$RID"}
]}]}
JSON
)
  aws ecs run-task \
    --cluster "$CLUSTER" \
    --task-definition "$TASKDEF" \
    --launch-type FARGATE \
    --count 1 \
    --network-configuration "$NETCFG" \
    --overrides "$OVERRIDES" \
    --region "$AWS_REGION" \
    --query "tasks[0].taskArn" --output text
done

echo "RunTask 요청 완료. CloudWatch Logs(/ecs/bada-perf-k6-runner)와 결과 S3(source-ips/, summaries/)를 확인하세요."
