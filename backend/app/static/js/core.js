// ===== 공통: 상태·헬퍼·언어적용·라우팅 (프론트 공통 소유) =====
let S={lang:"ko",caseId:null,analysis:null,chat:[]};
const t=k=>(T[S.lang][k]!=null?T[S.lang][k]:(T.ko[k]||k));
const ct=k=>((CHAT_TEXT[S.lang]&&CHAT_TEXT[S.lang][k]!=null)?CHAT_TEXT[S.lang][k]:CHAT_TEXT.ko[k]);
const won=n=>(n===null||n===undefined)?"-":Number(n).toLocaleString()+"원";
function toast(msg){let t=document.getElementById("toast");if(!t){t=document.createElement("div");t.id="toast";t.className="toast";(document.querySelector(".phone")||document.body).appendChild(t);}t.textContent=msg;t.classList.add("show");clearTimeout(window.__tT);window.__tT=setTimeout(()=>t.classList.remove("show"),3200);}
async function api(m,p,b){let r;try{const _h={"Content-Type":"application/json"};const _tk=(typeof getToken==="function")?getToken():"";if(_tk)_h["Authorization"]="Bearer "+_tk;r=await fetch(apiUrl(p),{method:m,headers:_h,body:b?JSON.stringify(b):undefined});}catch(e){toast("서버에 연결할 수 없어요. 네트워크·주소를 확인하세요.");throw e;}if(r.status===401){if(typeof clearToken==="function")clearToken();toast("로그인이 필요합니다.");if(typeof goLogin==="function")goLogin();throw new Error(await r.text());}if(!r.ok)throw new Error(await r.text());return r.status===204?null:r.json();}
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

function applyLang(){
  document.documentElement.lang = S.lang;
  document.querySelectorAll("[data-k]").forEach(e=>{e.innerHTML=t(e.getAttribute("data-k"));});
  document.getElementById("chatQuickPack").textContent=ct("pack");
  document.getElementById("chatQuickScript").textContent=ct("script");
  document.getElementById("chatQuickDocs").textContent=ct("docs");
  document.getElementById("chatQuickRisk").textContent=ct("risk");
  document.getElementById("chatInput").placeholder=ct("placeholder");
  // placeholder i18n
  document.querySelectorAll("[data-ph]").forEach(el=>{el.placeholder=t(el.getAttribute("data-ph"));});
  if(!S.chat.length)renderChat();
  const L=document.getElementById("lang");L.innerHTML="";
  const langs=[{code:"ko",label:"한국어"},{code:"vi",label:"Tiếng Việt"},{code:"en",label:"English"},{code:"id",label:"Indonesia"},{code:"km",label:"ខ្មែរ"},{code:"ne",label:"नेपाली"},{code:"th",label:"ไทย"},{code:"ja",label:"日本語"}];
  const sel=document.createElement("select");
  langs.forEach(l=>{const o=document.createElement("option");o.value=l.code;o.textContent=l.label;if(l.code===S.lang)o.selected=true;sel.appendChild(o);});
  sel.onchange=()=>{S.lang=sel.value;applyLang();};
  L.appendChild(sel);
  // 업로드 카드가 이미 렌더된 상태면 재렌더링
  if(S.caseId && document.getElementById("uploadCard") && document.getElementById("uploadCard").children.length > 0) {
    buildUpload();
  }
  // 문제 유형 칩 재렌더링
  const iss=document.getElementById("f_iss");
  if(iss && iss.children.length){
    const selected=[...iss.querySelectorAll(".chip-sel.on")].map(c=>c.dataset.v);
    iss.innerHTML="";
    Object.entries(ISSUES).forEach(([k,v])=>{const c=document.createElement("div");c.className="chip-sel";c.dataset.v=k;c.textContent=t(v);
      if(selected.includes(k))c.classList.add("on");
      c.onclick=()=>c.classList.toggle("on");iss.appendChild(c);});
  }
  // 결과 페이지에서 언어 변경 시 조용히 재분석 (로딩바 없이)
  if(S.analysis && S.caseId && document.getElementById("result").classList.contains("active")){
    toast(t("lang_changing")||"언어 변경중...");
    api("POST","/cases/"+S.caseId+"/analyze?lang="+S.lang,buildReq())
      .then(a=>{S.analysis=a;renderResult();})
      .catch(()=>{});
  }
}

function goPage(id,nav){
  document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  document.querySelectorAll(".nav-item").forEach(n=>n.classList.remove("active"));
  if(typeof nav==="number")document.querySelectorAll(".nav-item")[nav].classList.add("active");
  document.getElementById("screen").scrollTop=0;
}
function goUpload(){ S.caseId?goPage("upload",1):startNewCase(); }
function goResult(){ S.analysis?goPage("result",2):(S.caseId?goPage("upload",1):startNewCase()); }

// 상태바 시계: 실제 기기 시간으로 표시(분 단위 갱신)
function tickClock(){
  const el=document.getElementById("clock"); if(!el) return;
  const d=new Date();
  el.textContent=d.getHours().toString().padStart(2,"0")+":"+d.getMinutes().toString().padStart(2,"0");
}
tickClock(); setInterval(tickClock,15000);

// 상태바 네트워크: 실제 온라인/연결유형(웹 API, 미지원 시 안전 폴백)
function updateNet(){
  const ic=document.getElementById("netIcon"),tp=document.getElementById("netType");
  if(!ic||!tp)return;
  const on=navigator.onLine!==false;
  const conn=navigator.connection||navigator.mozConnection||navigator.webkitConnection;
  ic.className="ti "+(on?"ti-wifi":"ti-wifi-off");
  tp.textContent = !on ? "오프라인" : ((conn&&conn.effectiveType)?conn.effectiveType.toUpperCase():"온라인");
}
// 상태바 배터리: 실제 잔량·충전상태
function setBatt(level,charging){
  const pe=document.getElementById("battPct"),ic=document.getElementById("battIcon");
  if(!ic)return;
  const p=Math.round(level*100);
  if(pe)pe.textContent=p+"%";
  ic.className="ti "+(charging?"ti-battery-charging":(p>=88?"ti-battery-4":p>=63?"ti-battery-3":p>=38?"ti-battery-2":p>=13?"ti-battery-1":"ti-battery"));
}
function initStatusBar(){
  updateNet();
  window.addEventListener("online",updateNet);
  window.addEventListener("offline",updateNet);
  const conn=navigator.connection;
  if(conn&&conn.addEventListener)conn.addEventListener("change",updateNet);
  if(navigator.getBattery){
    navigator.getBattery().then(b=>{
      const u=()=>setBatt(b.level,b.charging);
      u();b.addEventListener("levelchange",u);b.addEventListener("chargingchange",u);
    }).catch(()=>{const e=document.getElementById("battPct");if(e)e.textContent="";});
  }else{
    const e=document.getElementById("battPct");if(e)e.textContent="";  // 배터리 API 미지원: %숨김
  }
}
initStatusBar();
