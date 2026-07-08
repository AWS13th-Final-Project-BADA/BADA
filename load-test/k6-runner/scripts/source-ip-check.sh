#!/usr/bin/env bash
# BADA 분산 k6 runner — external source IP 확인기
# 목적: 각 runner 태스크가 인터넷으로 나갈 때 보이는 external(공인) IP를 출력한다.
#       분산 검증에서 runner별 IP가 실제로 분산되는지(distinct count) 확인하는 데 쓴다.
#
# 단독 실행 또는 entrypoint에서 호출 가능. 결과는 stdout(JSON 1줄)으로 출력한다.
#   RUNNER_ID  runner 식별자(기본 hostname)
set -euo pipefail

RUNNER_ID="${RUNNER_ID:-$(hostname)}"

# 1차 checkip.amazonaws.com, 실패 시 api.ipify.org 폴백.
SRC_IP="$(curl -s --max-time 5 https://checkip.amazonaws.com || true)"
if [ -z "$SRC_IP" ]; then
  SRC_IP="$(curl -s --max-time 5 https://api.ipify.org || true)"
fi
SRC_IP="$(echo "${SRC_IP:-unknown}" | tr -d '[:space:]')"

printf '{"runner_id":"%s","source_ip":"%s","ts":"%s"}\n' \
  "$RUNNER_ID" "$SRC_IP" "$(date -u +%FT%TZ)"
