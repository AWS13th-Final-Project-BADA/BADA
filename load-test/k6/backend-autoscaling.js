// BADA Backend Auto Scaling 실증용 k6 부하 테스트 (#9)
//
// 목적: Backend ECS 서비스에 HTTP 부하를 걸어 CPU 사용률을 70% 이상으로 끌어올려
//       CPU Target Tracking Auto Scaling(#4)이 desired_count를 1 -> 2 -> 3으로
//       올리는 것(scale-out)과, 부하 종료 후 다시 줄이는 것(scale-in)을 유발한다.
//       Grafana/CloudWatch에서 CPU% 상승 + RunningTaskCount 증가 그래프를 캡처한다.
//
// 대상 엔드포인트: 기본 /health (DB/Bedrock 미사용 → 비용 0, 순수 웹서버 CPU만 소비).
//   Backend Task가 0.25 vCPU(256 CPU unit)로 작아, 수백 RPS면 CPU가 빠르게 70%를 넘는다.
//
// ⚠️ 공용 데모 환경(api.badasoft.com)에 부하를 건다. 반드시:
//   - 팀에 실행 시간대를 공지하고, 데모/리허설 시간과 겹치지 않게.
//   - 처음엔 낮은 RATE로 짧게 시험한 뒤 본 실행.
//
// 실행:
//   k6 run load-test/k6/backend-autoscaling.js
//   k6 run -e TARGET_URL=https://api.badasoft.com -e PEAK_RATE=200 load-test/k6/backend-autoscaling.js

import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.TARGET_URL || "https://api.badasoft.com";
const ENDPOINT = __ENV.ENDPOINT || "/health";
const PEAK_RATE = Number(__ENV.PEAK_RATE || 200); // 초당 요청 수(peak)

export const options = {
  scenarios: {
    scale_out_then_in: {
      executor: "ramping-arrival-rate",
      // 초당 요청 수 기준으로 부하를 제어(도착률). VU는 자동 할당.
      startRate: 20,
      timeUnit: "1s",
      preAllocatedVUs: 100,
      maxVUs: 500,
      stages: [
        { target: 40, duration: "2m" }, // warm-up: baseline CPU 확인
        { target: PEAK_RATE, duration: "3m" }, // ramp-up: CPU 70% 돌파 유도
        { target: PEAK_RATE, duration: "7m" }, // sustain: 알람 평가(약 3분) + scale-out cooldown(60s) 통과 → 1→2→3
        { target: 0, duration: "4m" }, // ramp-down: scale-in cooldown(300s) 관찰
      ],
    },
  },
  thresholds: {
    // 부하 목적이라 실패율/지연은 참고용(초과해도 테스트 자체는 계속).
    http_req_failed: [{ threshold: "rate<0.20", abortOnFail: false }],
    http_req_duration: ["p(95)<3000"],
  },
};

export default function () {
  const res = http.get(`${BASE}${ENDPOINT}`, {
    tags: { name: "backend_health" },
  });
  check(res, { "status is 200": (r) => r.status === 200 });
}

export function handleSummary(data) {
  // 콘솔 요약 + JSON 저장(리포트 첨부용).
  return {
    stdout: textSummary(data),
    "load-test/k6/last-run-summary.json": JSON.stringify(data, null, 2),
  };
}

// k6 기본 텍스트 요약 helper (별도 import 없이 최소 구현).
function textSummary(data) {
  const m = data.metrics;
  const line = (k, v) => `  ${k}: ${v}`;
  const reqs = m.http_reqs ? m.http_reqs.values.count : 0;
  const rps = m.http_reqs ? m.http_reqs.values.rate.toFixed(1) : "0";
  const p95 = m.http_req_duration ? m.http_req_duration.values["p(95)"].toFixed(0) : "0";
  const failRate = m.http_req_failed ? (m.http_req_failed.values.rate * 100).toFixed(2) : "0";
  return [
    "",
    "=== BADA Backend Auto Scaling 부하 테스트 요약 ===",
    line("총 요청", reqs),
    line("평균 RPS", rps),
    line("p95 지연(ms)", p95),
    line("실패율(%)", failRate),
    "",
    "→ Grafana(BADA Infrastructure)에서 Backend CPU% 와 ECS RunningTaskCount 그래프를 캡처하세요.",
    "",
  ].join("\n");
}
