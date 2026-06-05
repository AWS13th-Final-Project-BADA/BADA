/* BADA 서비스워커 — 앱 셸 오프라인 캐시.
   원칙: 정적 자산만 캐시. API(/cases,/chat,/files 등)와 POST는 절대 캐시하지 않음(데이터 신선도 보장). */
const CACHE = "bada-shell-v1";
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

  // GET 외(POST/PATCH/DELETE)·교차출처·API 경로는 캐시 우회 → 항상 네트워크
  const apiPath = /^\/(cases|chat|files|health|version|analysis)/.test(url.pathname);
  if (req.method !== "GET" || url.origin !== self.location.origin || apiPath) {
    return; // 기본 네트워크 처리
  }

  // 앱 셸/정적 자산: 캐시 우선, 없으면 네트워크 후 캐시에 저장
  e.respondWith(
    caches.match(req).then((hit) => {
      if (hit) return hit;
      return fetch(req).then((res) => {
        if (res.ok && (url.pathname === "/" || url.pathname.startsWith("/static/"))) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => caches.match("/"));
    })
  );
});
