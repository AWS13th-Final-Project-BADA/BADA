// BADA Backend Auto Scaling 실증용 k6 부하 테스트 (#9)
//
// 목적: Backend ECS 서비스에 부하를 걸어 CPU 사용률을 70% 이상으로 "꾸준히" 유지해
//       CPU Target Tracking Auto Scaling(#4)이 desired_count를 1 -> 2 -> 3으로
//       올리는 것(scale-out)과, 부하 종료 후 다시 줄이는 것(scale-in)을 유발한다.
//       Grafana/CloudWatch에서 CPU% 상승 + RunningTaskCount 증가 그래프를 캡처한다.
//
// ⚠️ 폐쇄형(closed-model) 부하를 쓴다: ramping-vus.
//   개방형(ramping-arrival-rate)은 0.25 vCPU 백엔드를 순식간에 포화시켜
//   타임아웃 폭주 -> 완료 요청 급감 -> CPU가 오히려 떨어져 3분 지속을 못 채운다.
//   폐쇄형은 각 VU가 응답을 받은 뒤 다음 요청을 보내므로 백엔드 용량에 맞춰
//   자체 조절되어, CPU가 70~100%에 안정적으로 머문다(스케일 알람 3분 충족).
//
// 스케일 알람 조건(확인됨): CPUUtilization > 70% 를 60초 x 3 = 3분 연속.
//
// ⚠️ 공용 데모 환경(api.badasoft.com)에 부하. 팀 공지 + 데모/리허설 시간 회피.
//
// 실행:
//   k6 run load-test/k6/backend-autoscaling.js
//   k6 run -e VUS=40 -e SUSTAIN=8m load-test/k6/backend-autoscaling.js
//   (CPU가 75% 밑에서 논다면 VUS를 올리고, 100% 붙어 타임아웃이 많으면 VUS를 낮춘다)

import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.TARGET_URL || "https://api.badasoft.com";
const ENDPOINT = __ENV.ENDPOINT || "/health";
const VUS = Number(__ENV.VUS || 40); // 동시 가상 사용자(폐쇄 루프)
const SUSTAIN = __ENV.SUSTAIN || "8m"; // peak 유지 시간(스케일아웃 3분 + 여유)

export const options = {
  scenarios: {
    scale_out_then_in: {
      executor: "ramping-vus",
      startVUs: 5,
      stages: [
        { target: VUS, duration: "3m" }, // ramp-up: CPU 70% 돌파
        { target: VUS, duration: SUSTAIN }, // sustain: CPU 70%+ 유지 -> 1→2→3
        { target: 0, duration: "3m" }, // ramp-down: scale-in(cooldown 300s) 관찰
      ],
      gracefulRampDown: "30s",
    },
  },
  thresholds: {
    // 부하 목적이라 실패율은 참고용(초과해도 테스트 계속). 폐쇄형이라 타임아웃은 거의 없어야 정상.
    http_req_failed: [{ threshold: "rate<0.30", abortOnFail: false }],
  },
};

export default function () {
  const res = http.get(`${BASE}${ENDPOINT}`, {
    tags: { name: "backend_health" },
    timeout: "20s", // 느린 요청은 빨리 실패시켜 VU가 무한 대기하지 않게
  });
  check(res, { "status is 200": (r) => r.status === 200 });
  // 아주 짧은 think-time: 완전 busy-loop을 피하되 CPU는 높게 유지.
  sleep(0.05);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data),
    "load-test/k6/last-run-summary.json": JSON.stringify(data, null, 2),
  };
}

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
