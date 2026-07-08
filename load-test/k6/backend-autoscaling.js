// BADA Backend Auto Scaling 실증용 k6 부하 테스트 (#9)
//
// 두 가지 MODE:
//   MODE=cpu     (기본) — 폐쇄형(ramping-vus) /health 부하로 CPU를 70%↑ 3분 유지 →
//                 CPU Target Tracking(#4)이 desired_count를 1→2→3으로 올리는 것을 "발동"시킨다.
//                 목적: 오토스케일링 "메커니즘이 실제로 동작"함을 증명. (지연은 /health라 무의미)
//   MODE=latency — 개방형(ramping-arrival-rate)으로 "실제 읽기 엔드포인트"(/community/boards, DB 조회)를
//                 1태스크 용량보다 살짝 높은 고정 rate로 밀어붙인다.
//                 목적: 리액티브 오토스케일링의 "scale-out 지연 구간"에서 p95가 어떻게
//                 저하됐다가 새 태스크 워밍업 후 회복되는지를 측정한다.
//
//   왜 모드를 나누나: 폐쇄형은 응답을 받아야 다음 요청을 보내 latency가 오르면 스스로 throughput을
//   줄여 "지연 진실"을 가린다(하지만 CPU는 안정적으로 높게 유지 → 알람 3분 충족에 유리).
//   개방형은 도착률을 고정해 포화 시 지연을 그대로 드러낸다(하지만 작은 태스크를 순식간에 포화시킬 수 있어
//   RATE 튜닝 필요). → 메커니즘 증명은 cpu, 지연 특성은 latency로 분리한다.
//
// 스케일 알람 조건(확인됨): CPUUtilization > 70% 를 60초 x 3 = 3분 연속. scale-in cooldown 300초.
// 스케일아웃 지연 = 감지(~3분) + Fargate 태스크 기동/부팅 + ALB 헬스체크 통과(interval 30s x healthy 2 ≈ 60s).
//
// ⚠️ 안전장치: TARGET_URL을 반드시 명시해야 하며(기본 운영 URL 폴백 없음), prod/dev URL이면 실행을 거부한다.
//    기본 허용 대상은 perf ALB DNS(http://bada-perf-*) 계열이다. 개발용 예외는 -e ALLOW_NON_PERF_TARGET=true.
//    팀 공지 + 데모/리허설 시간 회피, 낮은 값 시험 후 본 실행은 여전히 지킨다.
//
// 실행 (TARGET_URL 필수):
//   # 1) 메커니즘 증명 (기본)
//   k6 run -e TARGET_URL="$PERF_TARGET_URL" load-test/k6/backend-autoscaling.js
//   k6 run -e TARGET_URL="$PERF_TARGET_URL" -e VUS=50 -e SUSTAIN=8m load-test/k6/backend-autoscaling.js
//   # 2) 스케일아웃 지연 측정 (개방형, 실제 엔드포인트)
//   k6 run -e TARGET_URL="$PERF_TARGET_URL" -e MODE=latency load-test/k6/backend-autoscaling.js
//   k6 run -e TARGET_URL="$PERF_TARGET_URL" -e MODE=latency -e RATE=100 -e SUSTAIN=8m load-test/k6/backend-autoscaling.js
//   (개발 환경 대상은: -e TARGET_URL=<dev-url> -e ALLOW_NON_PERF_TARGET=true)
//   (cpu 모드: CPU가 75% 밑이면 VUS↑ / latency 모드: CPU 70%를 3분 못 넘기면 RATE↑, 타임아웃 폭주면 RATE↓)

import http from "k6/http";
import { check, sleep } from "k6";
import { resolveTarget } from "./_target-guard.js";

const BASE = resolveTarget(); // 안전장치: 미지정/운영·dev URL이면 init 단계에서 즉시 중단
const MODE = (__ENV.MODE || "cpu").toLowerCase(); // "cpu" | "latency"
const VUS = Number(__ENV.VUS || 40); // cpu 모드: 동시 가상 사용자(폐쇄 루프)
const RATE = Number(__ENV.RATE || 80); // latency 모드: 목표 초당 요청수(1태스크 용량 초과로 튜닝)
const MAX_VUS = Number(__ENV.MAX_VUS || 300); // latency 모드: 지연 상승 시 rate 유지를 위한 VU 상한
const SUSTAIN = __ENV.SUSTAIN || "8m"; // peak 유지 시간(스케일아웃 감지+워밍업+회복 관측 여유)
// cpu 모드는 CPU를 태우는 게 목적이라 일 안 하는 /health. latency 모드는 실제 DB 읽기 엔드포인트.
const ENDPOINT = __ENV.ENDPOINT || (MODE === "latency" ? "/community/boards" : "/health");

const cpuScenario = {
  executor: "ramping-vus",
  startVUs: 5,
  stages: [
    { target: VUS, duration: "3m" }, // ramp-up: CPU 70% 돌파
    { target: VUS, duration: SUSTAIN }, // sustain: CPU 70%+ 유지 -> 1→2→3
    { target: 0, duration: "3m" }, // ramp-down: scale-in(cooldown 300s) 관찰
  ],
  gracefulRampDown: "30s",
};

const latencyScenario = {
  executor: "ramping-arrival-rate", // 개방형: 도착률 고정 → 포화 시 지연을 그대로 노출
  startRate: 10,
  timeUnit: "1s",
  preAllocatedVUs: 50,
  maxVUs: MAX_VUS,
  stages: [
    { target: RATE, duration: "2m" }, // ramp: 1태스크 용량 초과 → CPU 70%↑, p95 상승 시작
    { target: RATE, duration: SUSTAIN }, // hold: scale-out 발동 + 새 태스크 워밍업 후 p95 회복 관측
    { target: 0, duration: "2m" }, // ramp-down
  ],
};

export const options = {
  scenarios:
    MODE === "latency" ? { scale_out_latency: latencyScenario } : { scale_out_then_in: cpuScenario },
  thresholds: {
    // 부하 목적이라 실패율은 참고용(초과해도 계속). 지연은 관측 대상이라 게이트 걸지 않는다.
    http_req_failed: [{ threshold: "rate<0.30", abortOnFail: false }],
  },
};

export default function () {
  const res = http.get(`${BASE}${ENDPOINT}`, {
    tags: { name: MODE === "latency" ? "backend_read" : "backend_health" },
    timeout: "20s", // 느린 요청은 빨리 실패시켜 VU가 무한 대기하지 않게
  });
  check(res, { "status is 200": (r) => r.status === 200 });
  // 개방형은 arrival-rate가 속도를 제어하므로 sleep 불필요. 폐쇄형만 짧은 think-time으로 busy-loop 방지.
  if (MODE !== "latency") sleep(0.05);
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
  const dur = m.http_req_duration ? m.http_req_duration.values : {};
  const p95 = dur["p(95)"] != null ? dur["p(95)"].toFixed(0) : "0";
  const p90 = dur["p(90)"] != null ? dur["p(90)"].toFixed(0) : "0";
  const avg = dur.avg != null ? dur.avg.toFixed(0) : "0";
  const failRate = m.http_req_failed ? (m.http_req_failed.values.rate * 100).toFixed(2) : "0";
  const capture =
    MODE === "latency"
      ? "→ Grafana(BADA Infrastructure): p95 지연 상승→회복 곡선을 'ECS Task Count(1→2→3)'와 같은 타임라인에 겹쳐 캡처."
      : "→ Grafana(BADA Infrastructure): Backend CPU% 70%↑ + ECS Task Count(RunningTaskCount 1→2→3) 그래프를 캡처.";
  return [
    "",
    `=== BADA Backend Auto Scaling 부하 요약 (MODE=${MODE}, endpoint=${ENDPOINT}) ===`,
    line("총 요청", reqs),
    line("평균 RPS", rps),
    line("지연 avg/p90/p95(ms)", `${avg} / ${p90} / ${p95}`),
    line("실패율(%)", failRate),
    "",
    capture,
    "  scaling 텍스트 증거: aws application-autoscaling describe-scaling-activities \\",
    "    --service-namespace ecs --region ap-northeast-2 --profile bada-team \\",
    "    --resource-id service/bada-dev-cluster/bada-dev-backend --output table",
    "",
  ].join("\n");
}
