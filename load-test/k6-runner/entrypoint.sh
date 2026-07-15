#!/usr/bin/env bash
# BADA 분산 k6 runner entrypoint — 안전장치 + source IP 기록 + k6 실행 + 결과 저장
#
# 필수 환경변수:
#   TARGET_URL   부하 대상 (반드시 perf ALB HTTP. dev/prod/운영 도메인이면 즉시 종료)
#   SCENARIO     k6 스크립트 파일명 (예: distributed-http.js)
# 선택:
#   VUS(기본 500) DURATION(기본 5m) RUNNER_ID(기본 hostname)
#   RESULT_S3_BUCKET  결과/소스IP 업로드 버킷 (없으면 로그로만 출력)
#   AWS_REGION(기본 ap-northeast-2)
set -euo pipefail

RUNNER_ID="${RUNNER_ID:-$(hostname)}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
VUS="${VUS:-500}"
DURATION="${DURATION:-5m}"
SCENARIO="${SCENARIO:-}"
TARGET_URL="${TARGET_URL:-}"
RESULT_S3_BUCKET="${RESULT_S3_BUCKET:-}"

log() { echo "[runner=$RUNNER_ID] $*"; }
die() { echo "[runner=$RUNNER_ID][FATAL] $*" >&2; exit 1; }

# ─── 안전장치 ─────────────────────────────────────────────────────────────
[ -n "$TARGET_URL" ] || die "TARGET_URL 미지정 → 실행 거부 (perf ALB DNS를 명시해야 함)"
[ -n "$SCENARIO" ]   || die "SCENARIO 미지정 → 실행 거부"

# 운영/dev/prod로 향하는 부하를 원천 차단.
case "$TARGET_URL" in
  *badasoft.com*)      die "운영 도메인(badasoft.com) 대상 금지 → 실행 거부: $TARGET_URL" ;;
  *api.badasoft*|*prod.badasoft*|*dev.badasoft*) die "dev/prod 대상 금지 → 실행 거부: $TARGET_URL" ;;
esac
# perf ALB 패턴(권장) 확인: bada-perf-alb-*.elb.amazonaws.com. 아니면 경고 후 종료.
case "$TARGET_URL" in
  http://bada-perf-alb-*.elb.amazonaws.com*|http://bada-perf-*) : ;;
  *) die "TARGET_URL이 perf ALB DNS 패턴이 아님 → 실행 거부(오작동 방지): $TARGET_URL" ;;
esac

[ -f "/work/scripts/$SCENARIO" ] || die "시나리오 파일 없음: /work/scripts/$SCENARIO"

# ─── source IP 기록 (분산 검증용) ─────────────────────────────────────────
SRC_IP="$(curl -s --max-time 5 https://checkip.amazonaws.com || echo unknown)"
SRC_IP="$(echo "$SRC_IP" | tr -d '[:space:]')"
log "external source IP = $SRC_IP"
log "TARGET_URL=$TARGET_URL SCENARIO=$SCENARIO VUS=$VUS DURATION=$DURATION"

# source IP를 S3에 기록(가능 시). 각 runner가 개별 객체로 남겨 distinct count 집계.
if [ -n "$RESULT_S3_BUCKET" ]; then
  echo "{\"runner_id\":\"$RUNNER_ID\",\"source_ip\":\"$SRC_IP\",\"target\":\"$TARGET_URL\",\"vus\":$VUS,\"duration\":\"$DURATION\",\"ts\":\"$(date -u +%FT%TZ)\"}" \
    > "/tmp/srcip-$RUNNER_ID.json"
  aws s3 cp "/tmp/srcip-$RUNNER_ID.json" "s3://$RESULT_S3_BUCKET/source-ips/$RUNNER_ID.json" --region "$AWS_REGION" || log "srcip S3 업로드 실패(무시)"
fi

# ─── k6 실행 ──────────────────────────────────────────────────────────────
SUMMARY="/tmp/summary-$RUNNER_ID.json"
set +e
k6 run \
  -e TARGET_URL="$TARGET_URL" \
  -e VUS="$VUS" \
  -e DURATION="$DURATION" \
  -e RUNNER_ID="$RUNNER_ID" \
  --summary-export="$SUMMARY" \
  "/work/scripts/$SCENARIO"
K6_RC=$?
set -e
log "k6 종료코드=$K6_RC"

if [ -n "$RESULT_S3_BUCKET" ] && [ -f "$SUMMARY" ]; then
  aws s3 cp "$SUMMARY" "s3://$RESULT_S3_BUCKET/summaries/$RUNNER_ID.json" --region "$AWS_REGION" || log "summary S3 업로드 실패(무시)"
fi

# k6 실패코드가 있어도 runner 자체는 정상 종료로 처리(부하테스트 threshold 실패는 정상 관측 대상)
exit 0
