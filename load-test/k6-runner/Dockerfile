# BADA 분산 k6 runner — ECS Fargate용 이미지
# 목적: 여러 runner 태스크를 각기 다른 public IP로 띄워, 단일 소스 IP 한계를 제거하고
#       실제 다수 사용자 분산 접속 조건을 재현한다. (앱 rate limit 정책은 그대로 둔다)
FROM grafana/k6:0.53.0

# k6 이미지는 비루트(uid 12345). curl/jq는 알파인 base에 없으므로 root로 설치.
USER root
RUN apk add --no-cache curl bash coreutils jq aws-cli

WORKDIR /work
COPY scripts/ /work/scripts/
COPY entrypoint.sh /work/entrypoint.sh
RUN chmod +x /work/entrypoint.sh /work/scripts/*.sh 2>/dev/null || true

# entrypoint가 안전장치 검사 후 k6를 실행한다.
ENTRYPOINT ["/work/entrypoint.sh"]
