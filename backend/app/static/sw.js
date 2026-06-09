/* BADA 서비스워커 — 앱 셸 오프라인 지원.
   전략: 네트워크 우선(network-first). 항상 최신을 먼저 가져오고,
        네트워크 실패(오프라인) 시에만 캐시로 폴백 → 변경/로그인 상태가 새로고침 없이 바로 반영.
   API(/cases,/chat,/auth 등)와 POST는 캐시하지 않음(데이터·인증 신선도 보장). */
const CACHE = "bada-shell-v2";
const SHELL = [
  "/",
  "/static/icon-192.png",
  "/static/icon-512.png",
  "/manifest.webmanifest",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);

  // GET 외(POST 등)·교차출처·동적 경로(API·인증)는 캐시 우회 → 항상 네트워크
  const dynamicPath = /^\/(cases|chat|files|health|version|analysis|auth)/.test(url.pathname);
  if (req.method !== "GET" || url.origin !== self.location.origin || dynamicPath) {
    return; // 기본 네트워크 처리
  }

  // 앱 셸/정적 자산: 네트워크 우선 → 성공 시 캐시 갱신, 실패 시 캐시 폴백
  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && (url.pathname === "/" || url.pathname.startsWith("/static/"))) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match("/")))
  );
});
