// ===== 소셜 로그인 + JWT 토큰 처리 =====
const BADA_TOKEN_KEY = "bada_token";

function getToken(){ try{ return localStorage.getItem(BADA_TOKEN_KEY) || ""; }catch(e){ return ""; } }
function setToken(t){ try{ localStorage.setItem(BADA_TOKEN_KEY, t); }catch(e){} }
function clearToken(){ try{ localStorage.removeItem(BADA_TOKEN_KEY); }catch(e){} }

// 소셜 로그인 시작
function kakaoLogin(){ location.href = apiUrl("/auth/kakao/login"); }
function naverLogin(){ if(typeof toast==="function") toast("네이버 로그인은 준비 중이에요."); }
function googleLogin(){ if(typeof toast==="function") toast("구글 로그인은 준비 중이에요."); }

function goLogin(){ if(typeof goPage==="function") goPage("login"); }

async function logout(){
  try{ await fetch(apiUrl("/auth/logout"), {method:"POST"}); }catch(e){}
  clearToken();
  if(typeof toast==="function") toast("로그아웃되었습니다.");
  renderAuth();
}

// 콜백 리다이렉트(#token=...)에서 토큰 회수 → 저장 → URL 정리.
function captureTokenFromUrl(){
  if(location.hash && location.hash.indexOf("token=")!==-1){
    const t = new URLSearchParams(location.hash.slice(1)).get("token");
    if(t){
      setToken(t);
      history.replaceState(null, "", location.pathname + location.search);
      if(typeof toast==="function") setTimeout(()=>toast("로그인되었습니다."),300);
    }
  }
}

async function fetchMe(){
  const tk = getToken();
  if(!tk) return null;
  try{
    const r = await fetch(apiUrl("/auth/me"), {headers:{Authorization:"Bearer "+tk}});
    if(r.status===401){ clearToken(); return null; }
    if(!r.ok) return null;
    return await r.json();
  }catch(e){ return null; }
}

// topbar 우측: 로그인 전=로그인 버튼 / 로그인 후=이름+로그아웃
async function renderAuth(){
  const box = document.getElementById("auth");
  if(!box) return;
  const me = await fetchMe();
  if(me && me.name){
    const initial = esc(me.name.slice(0,1));
    box.innerHTML =
      '<span class="auth-name"><span class="auth-avatar">'+initial+'</span>'+esc(me.name)+'</span>'+
      '<button class="auth-btn auth-out" onclick="logout()">로그아웃</button>';
    // 로그인 상태면 로그인 페이지를 떠나 홈으로
    const lp=document.getElementById("login");
    if(lp && lp.classList.contains("active") && typeof goPage==="function") goPage("home",0);
  }else{
    box.innerHTML = '<button class="auth-btn auth-login" onclick="goLogin()">로그인</button>';
  }
}

captureTokenFromUrl();
document.addEventListener("DOMContentLoaded", renderAuth);
