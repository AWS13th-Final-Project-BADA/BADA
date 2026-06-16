// ===== 환경 설정 (웹/앱 공용) =====
// 웹(FastAPI 서빙): BADA_API="" → 같은 출처로 호출 (기존 동작 그대로)
// 앱(Capacitor): mobile/sync-web.mjs 가 이 줄의 값을 백엔드 URL로 바꿔 넣음
window.BADA_API = window.BADA_API || "";
window.apiUrl = function (p) { return (window.BADA_API || "") + p; };

// 카카오 봇 연동: 채널 채팅 딥링크. 오픈빌더 채널의 채팅 URL로 교체하세요.
// 예: "http://pf.kakao.com/_xxxxx/chat" (비워두면 '채널 검색' 안내 토스트만 표시)
window.KAKAO_CHANNEL_URL = window.KAKAO_CHANNEL_URL || "";

// 네이티브 앱일 때만 동작 (웹/플러그인 없으면 조용히 무시)
(function () {
  try {
    if (!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform())) return;
    var P = window.Capacitor.Plugins || {};
    // 상태바: 흰 헤더에 맞춰 밝은 배경 + 어두운 아이콘
    if (P.StatusBar) {
      P.StatusBar.setStyle({ style: "DARK" });
      P.StatusBar.setBackgroundColor({ color: "#FFFFFF" });
    }
    // 안드로이드 뒤로가기: 홈이 아니면 홈으로, 홈이면 앱 종료
    if (P.App) {
      P.App.addListener("backButton", function () {
        var h = document.getElementById("home");
        if (h && !h.classList.contains("active") && typeof goPage === "function") {
          goPage("home", 0);
        } else {
          P.App.exitApp();
        }
      });
    }
  } catch (e) {}
})();
