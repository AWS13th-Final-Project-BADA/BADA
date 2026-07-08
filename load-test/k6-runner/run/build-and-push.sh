#!/usr/bin/env bash
# BADA 분산 k6 runner — 이미지 빌드 & ECR push (ARM64)
# setup-infra.sh가 만든 runner-env.sh(ECR_URL/AWS_REGION/AWS_PROFILE)를 자동 로드한다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_DIR="$(cd "$HERE/.." && pwd)"
[ -f "$HERE/runner-env.sh" ] && . "$HERE/runner-env.sh"

: "${ECR_URL:?ECR_URL 필요(setup-infra.sh 먼저 실행하거나 export)}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
AWS_PROFILE="${AWS_PROFILE:-bada-team}"
REGISTRY="${ECR_URL%/*}"

echo "[build] ECR 로그인: $REGISTRY"
aws ecr get-login-password --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  | docker login --username AWS --password-stdin "$REGISTRY"

echo "[build] buildx (linux/arm64) → push: $ECR_URL:latest"
docker buildx build --platform linux/arm64 -t "$ECR_URL:latest" --push "$RUNNER_DIR"

echo "[build] 완료: $ECR_URL:latest"
