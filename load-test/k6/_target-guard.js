// BADA k6 부하테스트 안전장치 (공용 모듈)
//
// 목적: 부하테스트가 실수로 운영(prod)·dev URL로 향하는 것을 막는다.
//   - TARGET_URL을 명시하지 않으면 실행 거부(기존처럼 운영 URL로 기본값 폴백하지 않음).
//   - prod/dev 도메인이면 실행 거부.
//   - 기본 허용 대상은 perf ALB DNS(`http://bada-perf-*`) 또는 `perf.badasoft.com` 계열.
//   - 개발용 등 예외가 필요하면 ALLOW_NON_PERF_TARGET=true 로 명시적으로 우회.
//
// 사용:
//   import { resolveTarget } from "./_target-guard.js";
//   const BASE = resolveTarget(); // init 단계에서 검증. 위반 시 throw → 테스트 즉시 중단.

// host만 정확히 비교해 substring 오탐(perf.badasoft.com ⊃ badasoft.com)을 피한다.
function hostOf(url) {
  return String(url)
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .split("/")[0]
    .split("?")[0]
    .split(":")[0];
}

// 운영/검증 도메인 — 이 host로는 절대 부하를 보내지 않는다.
const BLOCKED_HOSTS = [
  "badasoft.com",
  "api.badasoft.com",
  "prod.badasoft.com",
  "api.prod.badasoft.com",
  "dev.badasoft.com",
  "api.dev.badasoft.com",
];

// 명시적으로 허용되는 perf 도메인(도메인 위임 복구 시 옵션).
const ALLOWED_PERF_HOSTS = ["perf.badasoft.com", "api.perf.badasoft.com"];

export function resolveTarget() {
  const url = __ENV.TARGET_URL;
  const allowNonPerf = String(__ENV.ALLOW_NON_PERF_TARGET || "").toLowerCase() === "true";

  if (!url) {
    throw new Error(
      "TARGET_URL must be explicitly set to perf ALB DNS for load testing " +
        "(e.g. -e TARGET_URL=http://bada-perf-alb-xxxx.ap-northeast-2.elb.amazonaws.com). " +
        "For intentional non-perf runs set -e ALLOW_NON_PERF_TARGET=true."
    );
  }

  // 명시적 우회: 개발자가 의도적으로 non-perf 대상을 지정한 경우에만.
  if (allowNonPerf) {
    return url;
  }

  const host = hostOf(url);

  if (BLOCKED_HOSTS.indexOf(host) !== -1) {
    throw new Error(
      `Refusing to run load test against production/dev URL: ${url}. ` +
        "If this is intentional (non-perf), set -e ALLOW_NON_PERF_TARGET=true."
    );
  }

  const isPerf = host.indexOf("bada-perf-") === 0 || ALLOWED_PERF_HOSTS.indexOf(host) !== -1;
  if (!isPerf) {
    throw new Error(
      `TARGET_URL is not a recognized perf target: ${url}. ` +
        "Expected perf ALB DNS (http://bada-perf-*...) or api.perf.badasoft.com. " +
        "Set -e ALLOW_NON_PERF_TARGET=true to override."
    );
  }

  return url;
}
