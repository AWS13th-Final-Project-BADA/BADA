// ===== 카카오톡 봇 연동 (연동코드 발급 + 채널 안내) =====
// 로그인한 사용자가 6자리 코드를 받아 BADA 카톡 채널에 보내면 봇이 계정을 매핑한다.
// 채널 채팅 딥링크는 config.js의 window.KAKAO_CHANNEL_URL 로 설정 (예: http://pf.kakao.com/_xxxxx/chat)
const KAKAO_CHANNEL_URL = (window.KAKAO_CHANNEL_URL || "");

const LINK_T = {
  ko: {
    card_title: "카카오톡으로도 받기", card_sub: "연동하면 챗봇에서 내 사건을 확인해요",
    result_cta: "카톡으로도 확인하기",
    modal_title: "카카오톡 봇 연동", modal_sub: "아래 코드를 BADA 채널에 보내면 연동돼요",
    copy: "코드 복사", copied: "코드를 복사했어요",
    step1: "① '채널 열기'를 누르면 코드가 복사돼요", step2: "② 카톡 채팅창에 붙여넣고 전송", step3: "③ 연동 완료 — 봇에서 내 사건 확인",
    open_channel: "카카오톡 채널 열기",
    opening: "코드 복사됨 — 채팅창에 붙여넣고 전송하세요",
    qr_hint: "PC라면 휴대폰으로 QR을 스캔하세요",
    need_login: "연동하려면 먼저 로그인하세요", go_login: "로그인하기",
    issuing: "코드 발급 중…", err: "코드 발급에 실패했어요. 잠시 후 다시 시도해주세요",
    channel_todo: "채널 주소가 아직 설정되지 않았어요. 카카오톡에서 'BADA' 채널을 검색해 코드를 보내주세요"
  },
  en: {
    card_title: "Get updates on KakaoTalk", card_sub: "Link to check your case in the chatbot",
    result_cta: "Also check on KakaoTalk",
    modal_title: "Link KakaoTalk bot", modal_sub: "Send this code to the BADA channel to link",
    copy: "Copy code", copied: "Code copied",
    step1: "① Tap 'Open channel' — the code is copied", step2: "② Paste it in the chat and send", step3: "③ Done — view your case in the bot",
    open_channel: "Open KakaoTalk channel",
    opening: "Code copied — paste it in the chat and send",
    qr_hint: "On PC? Scan the QR with your phone",
    need_login: "Please log in first to link", go_login: "Log in",
    issuing: "Issuing code…", err: "Failed to issue code. Please try again",
    channel_todo: "Channel link not set yet. Search 'BADA' channel in KakaoTalk and send the code"
  },
  vi: {
    card_title: "Nhận trên KakaoTalk", card_sub: "Liên kết để xem hồ sơ trong chatbot",
    result_cta: "Xem thêm trên KakaoTalk",
    modal_title: "Liên kết bot KakaoTalk", modal_sub: "Gửi mã này tới kênh BADA để liên kết",
    copy: "Sao chép mã", copied: "Đã sao chép mã",
    step1: "① Nhấn 'Mở kênh' — mã sẽ được sao chép", step2: "② Dán vào chat và gửi", step3: "③ Xong — xem hồ sơ trong bot",
    open_channel: "Mở kênh KakaoTalk",
    opening: "Đã sao chép mã — dán vào chat và gửi",
    qr_hint: "Dùng PC? Quét QR bằng điện thoại",
    need_login: "Vui lòng đăng nhập trước để liên kết", go_login: "Đăng nhập",
    issuing: "Đang tạo mã…", err: "Tạo mã thất bại. Vui lòng thử lại",
    channel_todo: "Chưa đặt liên kết kênh. Tìm kênh 'BADA' trên KakaoTalk và gửi mã"
  }
};

function lt(k){
  const l = (typeof S !== "undefined" && S.lang) ? S.lang : "ko";
  const d = LINK_T[l] || LINK_T.ko;
  return (d[k] != null) ? d[k] : LINK_T.ko[k];
}

// 로그인 상태일 때만 홈 카드 노출. 결과 CTA는 항상 노출(모달이 비로그인 처리).
function refreshKakaoEntry(){
  const card = document.getElementById("kakaoLinkCard");
  if(card) card.style.display = (typeof getToken === "function" && getToken()) ? "block" : "none";
}

function applyLinkLang(){
  const set = (id, txt) => { const e = document.getElementById(id); if(e) e.textContent = txt; };
  set("kakaoCardTitle", lt("card_title"));
  set("kakaoCardSub", lt("card_sub"));
  set("kakaoResultCta", lt("result_cta"));
}

function _ensureLinkModal(){
  if(document.getElementById("kakaoLinkOverlay")) return;
  const ov = document.createElement("div");
  ov.id = "kakaoLinkOverlay";
  ov.style.cssText = "display:none;position:fixed;inset:0;background:rgba(0,0,0,0.45);z-index:9999;align-items:center;justify-content:center;padding:20px";
  ov.addEventListener("click", (e) => { if(e.target === ov) closeKakaoLink(); });
  ov.innerHTML =
    '<div style="width:100%;max-width:320px;background:#fff;color:#222;border-radius:14px;padding:18px;max-height:90vh;overflow:auto">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">' +
        '<strong id="kakaoModalTitle" style="font-size:16px"></strong>' +
        '<i class="ti ti-x" style="cursor:pointer;font-size:20px;color:#888" onclick="closeKakaoLink()" aria-label="close"></i>' +
      '</div>' +
      '<div id="kakaoLinkBody"></div>' +
    '</div>';
  document.body.appendChild(ov);
}

async function openKakaoLink(){
  _ensureLinkModal();
  const ov = document.getElementById("kakaoLinkOverlay");
  document.getElementById("kakaoModalTitle").textContent = lt("modal_title");
  const body = document.getElementById("kakaoLinkBody");
  ov.style.display = "flex";

  if(!(typeof getToken === "function" && getToken())){
    body.innerHTML =
      '<p style="font-size:14px;color:#666;margin:6px 0 14px">' + lt("need_login") + '</p>' +
      '<button class="primary-btn" style="width:100%" onclick="closeKakaoLink();if(typeof goLogin===\'function\')goLogin()">' + lt("go_login") + '</button>';
    return;
  }

  body.innerHTML = '<p style="text-align:center;color:#888;font-size:14px;padding:22px 0">' + lt("issuing") + '</p>';
  try{
    const r = await api("POST", "/auth/kakao/link-code");
    body.innerHTML = _codeHtml(r.code);
    _renderQR();
  }catch(e){
    body.innerHTML = '<p style="text-align:center;color:#c0392b;font-size:14px;padding:18px 0">' + lt("err") + '</p>';
  }
}

function _codeHtml(code){
  const safe = (typeof esc === "function") ? esc(code) : String(code);
  const qr = KAKAO_CHANNEL_URL
    ? ('<div style="text-align:center;margin-top:14px;padding-top:14px;border-top:1px solid #eee">' +
         '<div id="kakaoQR" style="display:inline-block"></div>' +
         '<p style="font-size:11px;color:#999;margin:8px 0 0">' + lt("qr_hint") + '</p>' +
       '</div>')
    : '';
  return '' +
    '<p style="font-size:13px;color:#666;margin:0 0 12px">' + lt("modal_sub") + '</p>' +
    '<div style="background:#f3f1ea;border-radius:8px;padding:14px;text-align:center;margin-bottom:8px">' +
      '<span id="kakaoCodeVal" style="font-size:26px;font-weight:500;letter-spacing:4px;font-family:monospace;color:#222">' + safe + '</span>' +
    '</div>' +
    '<button class="primary-btn ghost-btn" style="width:100%;margin-bottom:12px" onclick="copyKakaoCode()"><i class="ti ti-copy" aria-hidden="true"></i> ' + lt("copy") + '</button>' +
    '<div style="font-size:12px;color:#666;line-height:1.9;margin-bottom:12px">' +
      '<div>' + lt("step1") + '</div><div>' + lt("step2") + '</div><div>' + lt("step3") + '</div>' +
    '</div>' +
    '<button class="primary-btn" style="width:100%;background:#FEE500;color:#3C1E1E;border:none" onclick="openKakaoChannel()"><i class="ti ti-message-circle-2" aria-hidden="true"></i> ' + lt("open_channel") + '</button>' +
    qr;
}

function _renderQR(){
  const box = document.getElementById("kakaoQR");
  if(!box || !KAKAO_CHANNEL_URL || typeof QRCode === "undefined") return;
  box.innerHTML = "";
  try{ new QRCode(box, { text: KAKAO_CHANNEL_URL, width: 128, height: 128 }); }catch(e){}
}

function closeKakaoLink(){
  const ov = document.getElementById("kakaoLinkOverlay");
  if(ov) ov.style.display = "none";
}

function _copyText(code, msg){
  const ok = () => { if(typeof toast === "function") toast(msg); };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(code).then(ok).catch(() => _fallbackCopy(code, ok));
  }else{
    _fallbackCopy(code, ok);
  }
}

function copyKakaoCode(){
  const el = document.getElementById("kakaoCodeVal");
  if(el) _copyText(el.textContent.trim(), lt("copied"));
}

function _fallbackCopy(code, ok){
  try{
    const ta = document.createElement("textarea");
    ta.value = code; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    document.execCommand("copy"); document.body.removeChild(ta); ok();
  }catch(e){}
}

// 채널 열기: 코드를 자동 복사한 뒤 채널 채팅으로 이동 → 사용자는 붙여넣기만 하면 됨
function openKakaoChannel(){
  if(!KAKAO_CHANNEL_URL){
    if(typeof toast === "function") toast(lt("channel_todo"));
    return;
  }
  const el = document.getElementById("kakaoCodeVal");
  if(el) _copyText(el.textContent.trim(), lt("opening"));
  // noreferrer: referer(이전 페이지) 미전송 → 카카오 채널 진입 시 "이전 페이지: ..." 안내가 뜨지 않고
  // 바로 채팅이 시작돼 봇 웰컴(BADA 카드)이 노출됨. (카카오 공식: referer 미확인 시 이전 페이지 미표시)
  window.open(KAKAO_CHANNEL_URL, "_blank", "noopener,noreferrer");
}

// 언어 적용/인증 변경 시 진입점 텍스트·노출 갱신 (i18n.js·auth.js는 건드리지 않고 래핑)
(function(){
  const origAL = window.applyLang;
  window.applyLang = function(){ if(origAL) origAL.apply(this, arguments); applyLinkLang(); refreshKakaoEntry(); };
  const origRA = window.renderAuth;
  window.renderAuth = async function(){ if(origRA) await origRA.apply(this, arguments); refreshKakaoEntry(); };
})();
document.addEventListener("DOMContentLoaded", () => { applyLinkLang(); refreshKakaoEntry(); });
