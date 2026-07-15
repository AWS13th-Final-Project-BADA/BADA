// BADA "현실적 사용자 여정" 부하 테스트 (#9-a)
//
// 목적: /health CPU 스트레스(backend-autoscaling.js)와 달리, 실제 사용자가 만드는
//       읽기 트래픽 모양을 재현한다 — 인증 + DB 조회 + (분석 조회 시) 실시간 번역.
//       실제 백엔드 부하는 대부분 I/O 바운드라, CPU가 잘 안 오를 수 있다(정상/의도된 관찰).
//       => 이 테스트는 "동시 사용자 하에서의 지연/처리량/에러율"을 본다.
//          (오토스케일링 발동 증명은 backend-autoscaling.js의 CPU 스트레스로 별도 확보)
//
// 두 가지 모드:
//   - 토큰 없음(기본): 공개 엔드포인트만 (/community/boards=DB조회, /version). 셋업 0.
//   - 토큰 있음(-e TOKEN=<jwt>): 인증 여정(/auth/me, /cases, /community/posts, /community/boards).
//       * TOKEN은 로그인된 앱에서 얻거나(access_token), jwt_secret로 서명해 발급.
//       * -e CASE_ID=<id> 를 주면 분석 조회(/cases/{id}/analysis?lang=en) 포함 → Amazon Translate 경유(현실적 읽기).
//
// ⚠️ 안전장치: TARGET_URL을 반드시 명시해야 하며(기본 운영 URL 폴백 없음), prod/dev URL이면 실행을 거부한다.
//    기본 허용 대상은 perf ALB DNS(http://bada-perf-*) 계열이다. 개발용 예외는 -e ALLOW_NON_PERF_TARGET=true.
//    팀 공지 + 데모/리허설 시간 회피는 여전히 지킨다.
//
// 실행 (TARGET_URL 필수):
//   k6 run -e TARGET_URL="$PERF_TARGET_URL" load-test/k6/backend-journey.js                          # 공개 엔드포인트만
//   k6 run -e TARGET_URL="$PERF_TARGET_URL" -e TOKEN=<jwt> load-test/k6/backend-journey.js           # 인증 여정
//   k6 run -e TARGET_URL="$PERF_TARGET_URL" -e TOKEN=<jwt> -e CASE_ID=<case> -e VUS=40 load-test/k6/backend-journey.js
//   (개발 환경 대상은: -e TARGET_URL=<dev-url> -e ALLOW_NON_PERF_TARGET=true)

import http from "k6/http";
import { check, sleep } from "k6";
import { resolveTarget } from "./_target-guard.js";

const BASE = resolveTarget(); // 안전장치: 미지정/운영·dev URL이면 init 단계에서 즉시 중단
const TOKEN = __ENV.TOKEN || "";
const CASE_ID = __ENV.CASE_ID || "";
const VUS = Number(__ENV.VUS || 30); // 동시 사용자 수 (읽기 여정은 I/O 바운드라 여유 있게)
const SUSTAIN = __ENV.SUSTAIN || "6m";
const LANG = __ENV.LANG || "en";

const authHeaders = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};

export const options = {
  scenarios: {
    user_journey: {
      executor: "ramping-vus",
      startVUs: 3,
      stages: [
        { target: VUS, duration: "2m" },
        { target: VUS, duration: SUSTAIN },
        { target: 0, duration: "2m" },
      ],
      gracefulRampDown: "20s",
    },
  },
  thresholds: {
    http_req_failed: [{ threshold: "rate<0.10", abortOnFail: false }],
    http_req_duration: ["p(95)<3000"],
  },
};

function get(path, name, extraOk) {
  const res = http.get(`${BASE}${path}`, { headers: authHeaders, tags: { name } });
  const ok = { "status ok": (r) => r.status === 200 || (extraOk || []).includes(r.status) };
  check(res, ok);
  return res;
}

export default function () {
  // 공개: 로그인 화면/커뮤니티 진입 시 항상 부르는 것들
  get("/version", "version");
  get("/community/boards", "community_boards"); // DB 조회 (공개)

  if (TOKEN) {
    // 인증 여정: 앱 진입 후 사용자가 실제로 부르는 읽기 흐름
    get("/auth/me", "auth_me");
    get("/cases", "cases_list");
    get("/community/posts?sort=hot&limit=20", "community_feed");
    if (CASE_ID) {
      // 분석 결과 조회 (lang!=ko 면 Amazon Translate 실시간 번역 → 현실적 CPU+외부호출)
      get(`/cases/${CASE_ID}/analysis?lang=${LANG}`, "analysis_view", [404]);
    }
  }

  // 사용자 think-time: 화면 보고 다음 액션까지 1~3초
  sleep(1 + Math.random() * 2);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data),
    "load-test/k6/last-journey-summary.json": JSON.stringify(data, null, 2),
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
    "=== BADA 사용자 여정 부하 요약 ===",
    line("모드", TOKEN ? "인증 여정" + (CASE_ID ? " + 분석조회" : "") : "공개 엔드포인트"),
    line("총 요청", reqs),
    line("평균 RPS", rps),
    line("p95 지연(ms)", p95),
    line("실패율(%)", failRate),
    "",
    "→ 읽기 여정은 I/O 바운드라 CPU가 낮을 수 있음(정상). 지연/처리량/에러율 위주로 캡처.",
    "",
  ].join("\n");
}
