// ===== 공통: 상태·헬퍼·언어적용·라우팅 (프론트 공통 소유) =====
let S={lang:"ko",caseId:null,analysis:null,chat:[]};
const t=k=>(T[S.lang][k]!=null?T[S.lang][k]:(T.ko[k]||k));
const ct=k=>(CHAT_TEXT[S.lang][k]!=null?CHAT_TEXT[S.lang][k]:CHAT_TEXT.ko[k]);
const won=n=>(n===null||n===undefined)?"-":Number(n).toLocaleString()+"원";
async function api(m,p,b){const r=await fetch(p,{method:m,headers:{"Content-Type":"application/json"},body:b?JSON.stringify(b):undefined});if(!r.ok)throw new Error(await r.text());return r.status===204?null:r.json();}
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

function applyLang(){
  document.querySelectorAll("[data-k]").forEach(e=>{e.innerHTML=t(e.getAttribute("data-k"));});
  document.getElementById("chatQuickPack").textContent=ct("pack");
  document.getElementById("chatQuickScript").textContent=ct("script");
  document.getElementById("chatQuickDocs").textContent=ct("docs");
  document.getElementById("chatQuickRisk").textContent=ct("risk");
  document.getElementById("chatInput").placeholder=ct("placeholder");
  if(!S.chat.length)renderChat();
  const L=document.getElementById("lang");L.innerHTML="";
  const langs=[{code:"ko",label:"한국어"},{code:"vi",label:"Tiếng Việt"},{code:"en",label:"English"},{code:"id",label:"Indonesia"},{code:"km",label:"ខ្មែរ"},{code:"ne",label:"नेपाली"},{code:"th",label:"ไทย"},{code:"ja",label:"日本語"}];
  const sel=document.createElement("select");
  langs.forEach(l=>{const o=document.createElement("option");o.value=l.code;o.textContent=l.label;if(l.code===S.lang)o.selected=true;sel.appendChild(o);});
  sel.onchange=()=>{S.lang=sel.value;applyLang();};
  L.appendChild(sel);
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
