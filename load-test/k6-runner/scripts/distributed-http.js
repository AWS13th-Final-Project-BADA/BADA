// BADA 분산 k6 runner — HTTP 부하 시나리오
// 목적: 여러 runner(각기 다른 source IP)에서 동시에 실행해 실제 다수 사용자 분산 접속을 재현.
// 각 runner는 VUS/DURATION만큼 부하를 주고, status code 분포(429 vs 5xx)와 p95/p99/RPS/error rate를 기록.
//
// 실행(컨테이너 entrypoint가 주입): -e TARGET_URL, -e VUS, -e DURATION, -e RUNNER_ID
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE = __ENV.TARGET_URL; // entrypoint 안전장치가 perf ALB만 허용
const VUS = Number(__ENV.VUS || 500);
const DURATION = __ENV.DURATION || "5m";
const RUNNER_ID = __ENV.RUNNER_ID || "runner";

// status code 분포를 명시적으로 집계 (429 = 앱 rate limit / 5xx = 서버 오류 구분)
const c2xx = new Counter("status_2xx");
const c4xx = new Counter("status_4xx");
const c429 = new Counter("status_429");
const c5xx = new Counter("status_5xx");

export const options = {
  scenarios: {
    distributed: {
      executor: "constant-vus",
      vus: VUS,
      duration: DURATION,
    },
  },
  thresholds: {
    // 관측 목적 — 실패해도 계속 진행(부하테스트에서 threshold 실패는 정상 신호)
    http_req_failed: [{ threshold: "rate<0.50", abortOnFail: false }],
  },
};

// 비면제 엔드포인트(DB 읽기). rate limit이 걸리는 실제 경로.
const READ_PATHS = ["/community/boards", "/cases", "/community/posts?sort=hot&limit=20"];

export default function () {
  const path = READ_PATHS[Math.floor(Math.random() * READ_PATHS.length)];
  const res = http.get(`${BASE}${path}`, { tags: { name: "read" }, timeout: "20s" });
  const s = res.status;
  if (s >= 200 && s < 300) c2xx.add(1);
  else if (s === 429) { c429.add(1); c4xx.add(1); }
  else if (s >= 400 && s < 500) c4xx.add(1);
  else if (s >= 500) c5xx.add(1);
  check(res, { "status 2xx": (r) => r.status >= 200 && r.status < 300 });
  sleep(0.2 + Math.random() * 0.5); // think-time
}

export function handleSummary(data) {
  const m = data.metrics;
  const v = (k) => (m[k] && m[k].values ? m[k].values : {});
  const cnt = (k) => (m[k] && m[k].values ? m[k].values.count : 0);
  const dur = v("http_req_duration");
  const out = {
    runner_id: RUNNER_ID,
    target: BASE,
    vus: VUS,
    duration: DURATION,
    total_requests: cnt("http_reqs"),
    rps: m.http_reqs ? Number(m.http_reqs.values.rate.toFixed(1)) : 0,
    p95_ms: dur["p(95)"] != null ? Number(dur["p(95)"].toFixed(1)) : null,
    p99_ms: dur["p(99)"] != null ? Number(dur["p(99)"].toFixed(1)) : null,
    error_rate: m.http_req_failed ? Number((m.http_req_failed.values.rate * 100).toFixed(2)) : null,
    status_2xx: cnt("status_2xx"),
    status_4xx: cnt("status_4xx"),
    status_429: cnt("status_429"),
    status_5xx: cnt("status_5xx"),
  };
  return {
    stdout:
      `\n=== runner ${RUNNER_ID} 요약 ===\n` +
      `총요청 ${out.total_requests} · RPS ${out.rps} · p95 ${out.p95_ms}ms · p99 ${out.p99_ms}ms · err ${out.error_rate}%\n` +
      `2xx ${out.status_2xx} / 4xx ${out.status_4xx}(429 ${out.status_429}) / 5xx ${out.status_5xx}\n`,
    "/tmp/runner-summary.json": JSON.stringify(out, null, 2),
  };
}
