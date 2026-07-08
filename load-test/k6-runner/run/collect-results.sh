#!/usr/bin/env bash
# BADA 분산 k6 runner — 결과 수집 & source IP 분산 검증
# 결과 S3(source-ips/, summaries/)를 내려받아 distinct external IP 수와 runner 요약을 집계한다.
# runner-env.sh(RESULT_S3_BUCKET/AWS_REGION/AWS_PROFILE)를 자동 로드한다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$HERE/runner-env.sh" ] && . "$HERE/runner-env.sh"

: "${RESULT_S3_BUCKET:?RESULT_S3_BUCKET 필요(setup-infra.sh 먼저 실행하거나 export)}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
AWS_PROFILE="${AWS_PROFILE:-bada-team}"
OUT="${OUT:-./runner-results}"

aws() { command aws --region "$AWS_REGION" --profile "$AWS_PROFILE" "$@"; }

mkdir -p "$OUT/source-ips" "$OUT/summaries"
echo "[collect] s3://$RESULT_S3_BUCKET → $OUT"
aws s3 cp "s3://$RESULT_S3_BUCKET/source-ips/"  "$OUT/source-ips/"  --recursive || true
aws s3 cp "s3://$RESULT_S3_BUCKET/summaries/"   "$OUT/summaries/"   --recursive || true

echo
echo "=== source IP 분산 검증 ==="
if ls "$OUT"/source-ips/*.json >/dev/null 2>&1; then
  RUNNERS_SEEN="$(ls "$OUT"/source-ips/*.json | wc -l | tr -d ' ')"
  # jq가 있으면 정확히, 없으면 grep 폴백.
  if command -v jq >/dev/null 2>&1; then
    DISTINCT="$(cat "$OUT"/source-ips/*.json | jq -r '.source_ip' | sort -u | tee "$OUT/distinct-ips.txt" | wc -l | tr -d ' ')"
  else
    DISTINCT="$(cat "$OUT"/source-ips/*.json | grep -o '"source_ip":"[^"]*"' | sed 's/.*://; s/"//g' | sort -u | tee "$OUT/distinct-ips.txt" | wc -l | tr -d ' ')"
  fi
  echo "runner 결과 파일: $RUNNERS_SEEN, distinct external IP: $DISTINCT"
  echo "distinct IP 목록:"; cat "$OUT/distinct-ips.txt"
  echo
  if [ "$DISTINCT" -ge 2 ] && [ "$DISTINCT" -ge $((RUNNERS_SEEN / 2)) ]; then
    echo "[PASS] source IP가 분산됨 → 대규모(5,000~10,000 VU) 단계 진행 가능"
  else
    echo "[FAIL] source IP 분산 부족(distinct=$DISTINCT). public subnet/assignPublicIp/NAT 구성 재확인 필요."
    echo "       → 분산 검증 실패 상태에서 5,000 VU 이상 진행하면 rate limit(429)만 쌓인다. 진행 금지."
  fi
else
  echo "source-ips 결과 없음. runner가 실행됐는지, RESULT_S3_BUCKET이 맞는지 확인하세요."
fi
