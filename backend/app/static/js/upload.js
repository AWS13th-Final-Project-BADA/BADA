// ===== 업로드·촬영·OCR 추출·편집 (OCR 담당 소유) =====
const ROWS=[
 {cat:"contract",icon:"📄",bg:"soft-blue",t:"근로계약서",s:"임금 조건, 공제 조건"},
 {cat:"statement",icon:"🧾",bg:"soft-green",t:"급여명세서",s:"지급액, 공제 항목"},
 {cat:"payment",icon:"🏦",bg:"soft-orange",t:"입금내역",s:"실제 입금액 비교"},
 {cat:"chat",icon:"💬",bg:"soft-blue",t:"대화 캡처",s:"지급 약속, 공제 설명"},
 {cat:"other",icon:"🌏",bg:"soft-green",t:"모국어 메모",s:"상담용 문장 변환"}
];


async function preprocessImage(file){
  if(!file.type.startsWith("image/")) return {blob:file,name:file.name,warn:null};
  try{
    const bmp=await createImageBitmap(file,{imageOrientation:"from-image"});
    const MAX=2200, scale=Math.min(1,MAX/Math.max(bmp.width,bmp.height));
    const w=Math.round(bmp.width*scale), h=Math.round(bmp.height*scale);
    const cv=document.createElement("canvas"); cv.width=w; cv.height=h;
    cv.getContext("2d").drawImage(bmp,0,0,w,h);
    const blob=await new Promise(res=>cv.toBlob(res,"image/jpeg",0.85));
    const longSide=Math.max(bmp.width,bmp.height);
    const warn = longSide<1100 ? "해상도가 낮아 글자 인식이 어려울 수 있어요. 더 가까이·밝게 다시 찍어보세요."
      : (bmp.width>bmp.height*2.2 ? "캡처가 길어요 — 핵심 문장 앞뒤가 잘리지 않았는지 확인하세요." : null);
    const name=(file.name||"photo").replace(/\.(png|jpe?g|webp|heic)$/i,"")+".jpg";
    return {blob:blob||file, name, warn};
  }catch(e){ return {blob:file,name:file.name,warn:null}; }
}

async function doUpload(cat, file, btn, warnEl){
  const {blob,name,warn}=await preprocessImage(file);
  warnEl.textContent = warn||"";
  const fd=new FormData(); fd.append("category",cat); fd.append("file",blob,name);
  btn.textContent="업로드 중...";
  try{
    const res=await fetch("/cases/"+S.caseId+"/evidences/upload",{method:"POST",body:fd});
    if(!res.ok) throw new Error(await res.text());
    btn.textContent="완료 ✓"; btn.classList.add("done");
  }catch(e){ btn.textContent="다시"; alert("업로드 실패: "+e.message); }
}

function buildUpload(){
  const c=document.getElementById("uploadCard");c.innerHTML="";
  ROWS.forEach(r=>{
    const row=document.createElement("div");row.className="upload-row";
    row.innerHTML=`<div class="upload-left"><div class="file-icon ${r.bg}">${r.icon}</div>
      <div><strong>${r.t}</strong><span>${r.s}</span><span class="need" style="color:#b45309"></span></div></div>
      <div style="display:flex;gap:6px;align-items:center">
        <button class="upload-chip cam" title="촬영">📷</button>
        <button class="upload-chip gal">파일</button>
      </div>
      <input type="file" accept="image/*" capture="environment" class="i-cam" style="display:none">
      <input type="file" accept="image/*,application/pdf" class="i-gal" style="display:none">`;
    const camBtn=row.querySelector(".cam"), galBtn=row.querySelector(".gal");
    const iCam=row.querySelector(".i-cam"), iGal=row.querySelector(".i-gal");
    const warnEl=row.querySelector(".need");
    camBtn.onclick=()=>iCam.click(); galBtn.onclick=()=>iGal.click();
    iCam.onchange=()=>{ if(iCam.files.length) doUpload(r.cat,iCam.files[0],camBtn,warnEl); };
    iGal.onchange=()=>{ if(iGal.files.length) doUpload(r.cat,iGal.files[0],galBtn,warnEl); };
    c.appendChild(row);
  });
}

const _esc=(s)=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
const _catLabel=(c)=>{const r=ROWS.find(x=>x.cat===c);return r?r.t:c;};
const _won=(n)=>Number(n).toLocaleString()+"원";

function renderSanity(items){
  return items.map(s=>`<div style="margin-top:8px;padding:8px 10px;background:#fff7ed;border-radius:8px;border-left:3px solid #f59e0b">
    <div style="font-size:12px;font-weight:700;color:#b45309">⚠ ${_esc(s.field)} 값 확인 필요</div>
    <div class="small-muted">${_esc(s.note)}</div></div>`).join("");
}
function renderQuality(q){
  const color={high:"#047857",medium:"#b45309",low:"#b91c1c"}[q.level]||"#6b7280";
  const lvl={high:"증거력 높음",medium:"증거력 보통",low:"증거력 낮음"}[q.level]||q.level;
  const chk=Object.entries(q.checklist||{}).map(([k,v])=>`<span class="tag" style="background:${v?'#e8fbf3':'#f3f4f6'};color:${v?'#047857':'#9ca3af'}">${v?'✓':'·'} ${k}</span>`).join(" ");
  const warn=(q.warnings||[]).map(w=>`<div class="need" style="font-weight:600">⚠ ${_esc(w)}</div>`).join("");
  return `<div style="margin-top:10px;padding:10px;background:#f8fafc;border-radius:10px">
    <div style="font-size:13px;font-weight:800;color:${color}">증거력 ${q.score}/${q.max_score} · ${lvl}</div>
    <div style="margin:6px 0">${chk}</div>${warn}</div>`;
}

S.ext={};  // evidence_id -> 최신 엔티티(편집 기준값)

// 근거 confidence에서 amount label -> level 매핑
function _confMap(e){const m={};((e.confidence&&e.confidence.amounts)||[]).forEach(a=>{m[a.label]=a.level;});return m;}
function _lowStyle(level){return level==="low"?"background:#fff7ed;border-color:#f59e0b":"";}

// 편집용 인풋(스칼라). eid+key로 DOM id 구성.
function _fld(eid,key,labelTxt,val,type){
  const v=(val==null?"":val);
  return `<label style="margin:8px 0 3px">${labelTxt}</label>
    <input id="sc_${eid}_${key}" type="${type||'text'}" value="${_esc(v)}" style="padding:9px 11px"/>`;
}

function renderCardBody(e){
  if(e.ocr_status==="processing"||e.ocr_status==="pending"){
    return "<p class='small-muted'>⏳ 읽는 중...</p>";
  }
  if(e.ocr_status!=="done"){
    return "<p class='small-muted'>"+_esc(e.error||e.ocr_text||"읽기 실패")+"</p>"+
      "<button class='upload-chip' style='margin-top:8px' onclick=\"runExtract()\">다시 시도</button>";
  }
  const en=e.entities||{}, eid=e.evidence_id, cm=_confMap(e);
  S.ext[eid]=en;
  // 금액 편집 행 (저신뢰는 노랑 강조)
  const amts=(en.amounts||[]).map((a,i)=>{
    const lv=cm[a.label]||"medium";
    return `<div class="amt-row" style="display:flex;gap:6px;margin-top:5px;align-items:center">
      <input class="amt-label" value="${_esc(a.label||"")}" placeholder="항목" style="flex:1.2;padding:8px 9px"/>
      <input class="amt-val" type="number" value="${a.value==null?"":a.value}" placeholder="금액" style="flex:1;padding:8px 9px;${_lowStyle(lv)}"/>
      ${lv==="low"?'<span title="확인 필요" style="color:#b45309">⚠</span>':''}</div>`;
  }).join("");
  const deds=(en.deductions||[]).map((d)=>
    `<div class="ded-row" style="display:flex;gap:6px;margin-top:5px">
      <input class="ded-name" value="${_esc(d.name||"")}" placeholder="공제명" style="flex:1.2;padding:8px 9px"/>
      <input class="ded-val" type="number" value="${d.amount==null?"":d.amount}" placeholder="금액" style="flex:1;padding:8px 9px"/></div>`).join("");
  const utt=(en.utterances||[]).length
    ? "<div class='small-muted' style='margin-top:8px'>발화: "+en.utterances.map(u=>_esc(u.speaker||"?")+' "'+_esc((u.text||"").slice(0,24))+'"').join(" · ")+"</div>" : "";
  return `<div style="font-size:12px">
    <div class="frow">
      <div>${_fld(eid,"hourly_wage","시급(원)·손글씨면 확인",en.hourly_wage,"number")}</div>
      <div>${_fld(eid,"monthly_wage","월급(원)",en.monthly_wage,"number")}</div>
    </div>
    <div class="frow">
      <div>${_fld(eid,"work_days","근무일수",en.work_days,"number")}</div>
      <div>${_fld(eid,"pay_date","지급일",en.pay_date,"text")}</div>
    </div>
    <div class="frow">
      <div>${_fld(eid,"overtime_hours","연장(h)",en.overtime_hours,"number")}</div>
      <div>${_fld(eid,"night_hours","야간(h)",en.night_hours,"number")}</div>
      <div>${_fld(eid,"holiday_hours","휴일(h)",en.holiday_hours,"number")}</div>
    </div>
    <label style="margin:8px 0 3px">금액 항목</label>${amts||'<span class="small-muted">없음</span>'}
    <label style="margin:10px 0 3px">공제 항목</label>${deds||'<span class="small-muted">없음</span>'}
    ${utt}
    <button class="primary-btn" style="margin-top:12px;padding:11px" onclick="saveEntities('${eid}')">✏️ 수정 저장</button>
    <span id="save_${eid}" class="small-muted" style="margin-left:8px"></span>
    ${e.evidence_quality?renderQuality(e.evidence_quality):""}
    ${e.sanity&&e.sanity.length?renderSanity(e.sanity):""}
    ${e.ocr_text?"<details style='margin-top:6px'><summary class='small-muted' style='cursor:pointer'>읽은 원문 보기</summary><pre style='white-space:pre-wrap;font-size:12px;color:#374151;background:#f8fafc;padding:8px;border-radius:8px;max-height:180px;overflow:auto'>"+_esc(e.ocr_text)+"</pre></details>":""}
  </div>`;
}

function renderCard(e){
  const badge = e.ocr_status==="done"
    ? "<span class='tag' style='background:#e8fbf3;color:#047857'>읽음</span>"
    : (e.ocr_status==="processing"||e.ocr_status==="pending")
      ? "<span class='tag' style='background:#eef2ff;color:#2563eb'>읽는 중</span>"
      : "<span class='tag' style='background:#fef2f2;color:#b91c1c'>실패</span>";
  return `<div class="card" id="card_${e.evidence_id}" style="margin:8px 0;padding:14px">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
      <strong style="font-size:13px">${_esc(e.file_name||"")} <span class='tag'>${_esc(_catLabel(e.category))}</span></strong>${badge}</div>
    ${renderCardBody(e)}</div>`;
}

function renderExtract(r){
  const ev=r.evidences||[];
  if(!ev.length) return "";
  return "<h3 style='margin:14px 0 6px'>🔍 AI가 읽은 내용 <span class='small-muted' style='font-weight:400'>· 값을 직접 고칠 수 있어요</span></h3>"+ev.map(renderCard).join("");
}

const _num=v=>{const s=String(v).replace(/[^0-9.\-]/g,"");return s===""?null:(s.indexOf(".")>=0?parseFloat(s):parseInt(s));};
async function saveEntities(eid){
  const card=document.getElementById("card_"+eid); if(!card)return;
  const base=JSON.parse(JSON.stringify(S.ext[eid]||{}));
  ["hourly_wage","monthly_wage","work_days","overtime_hours","night_hours","holiday_hours"].forEach(k=>{
    const el=document.getElementById("sc_"+eid+"_"+k); if(el) base[k]=_num(el.value);
  });
  const pd=document.getElementById("sc_"+eid+"_pay_date"); if(pd) base.pay_date=pd.value||null;
  base.amounts=[...card.querySelectorAll(".amt-row")].map(r=>({
    label:r.querySelector(".amt-label").value||null, value:_num(r.querySelector(".amt-val").value)}))
    .filter(a=>a.label||a.value!=null);
  base.deductions=[...card.querySelectorAll(".ded-row")].map(r=>({
    name:r.querySelector(".ded-name").value||null, amount:_num(r.querySelector(".ded-val").value)}))
    .filter(d=>d.name||d.amount!=null);
  const note=document.getElementById("save_"+eid); if(note)note.textContent="저장 중...";
  try{
    const row=await api("PATCH","/cases/"+S.caseId+"/evidences/"+eid+"/entities",{entities:base});
    card.outerHTML=renderCard(row);   // 갱신(sanity·confidence 재계산 반영)
    // 시급을 고쳤으면 분석 입력값에도 반영
    if(row.entities&&row.entities.hourly_wage) document.getElementById("n_hw").value=row.entities.hourly_wage;
  }catch(e){ if(note)note.textContent="저장 실패: "+e.message; }
}

function setFlowStep(n){  // 1..4 현재 단계 강조, 이전은 done
  document.querySelectorAll("#flowSteps .fstep").forEach((el,i)=>{
    el.classList.toggle("done",i<n-1); el.classList.toggle("on",i===n-1);
  });
}

function _fillNumbox(r){
  if(r.agreed_hourly_wage) document.getElementById("n_hw").value=r.agreed_hourly_wage;
  if(r.worked_hours&&r.worked_hours.length) document.getElementById("n_hrs").value=r.worked_hours.join(",");
  if(r.deposits&&r.deposits.length) document.getElementById("n_dep").value=r.deposits.map(d=>`${d.date||""}, ${d.amount}`).join("\n");
  if(r.deductions&&r.deductions.length) document.getElementById("n_ded").value=r.deductions.map(d=>`${d.name}, ${d.amount}`).join("\n");
}

async function runExtract(){
  if(!S.caseId){alert("먼저 사건을 만들어주세요.");return;}
  setFlowStep(2);
  const st=document.getElementById("extractStatus");
  const det=document.getElementById("extractDetail");
  st.textContent="AI가 자료를 읽는 중..."; det.innerHTML="";
  try{
    // 1) 비동기 OCR 시작(즉시 반환) → 처리중 카드 렌더
    const first=await api("POST","/cases/"+S.caseId+"/evidences/extract");
    det.innerHTML=renderExtract(first);
    if(!(first.evidences||[]).length){ st.textContent="업로드된 파일이 없습니다. 먼저 자료를 올려주세요."; setFlowStep(1); return; }
    // 2) 완료까지 폴링
    const poll=async()=>{
      let r; try{ r=await api("GET","/cases/"+S.caseId+"/evidences/extract"); }catch(e){ st.textContent="상태 확인 실패: "+e.message; return; }
      det.innerHTML=renderExtract(r);
      if(r.status==="processing"){ st.textContent="AI가 자료를 읽는 중... ⏳"; setTimeout(poll,1500); return; }
      // 완료
      _fillNumbox(r);
      document.querySelector("details.numbox").open=true;
      const n=(r.worked_hours||[]).length+(r.deposits||[]).length+(r.deductions||[]).length;
      st.textContent = n===0 ? "읽기 완료 — 아래 'AI가 읽은 내용'을 확인·수정하세요."
        : "읽기 완료 — 값이 맞는지 확인하고, 틀리면 직접 고쳐 저장하세요."+(r.needs_review?" (확인 필요)":"");
      setFlowStep(3);
    };
    setTimeout(poll,1200);
  }catch(e){ st.textContent="추출 실패: "+e.message; }
}
function fillDemo(){
  document.getElementById("n_hrs").value="174,168,180,176";
  document.getElementById("n_dep").value="2026-01-15, 1500000\n2026-02-15, 1600000\n2026-03-15, 1550000\n2026-04-15, 1600000";
  document.getElementById("n_ded").value="기숙사비, 250000\n식비, 150000\n작업복비, 80000\n관리비 명목, 50000";
  document.getElementById("n_gchk").checked=true;document.getElementById("gbox").style.display="block";
  document.getElementById("n_wp").value="37.5000,127.0000,50";
  document.getElementById("n_png").value="2026-01-15T09:05:00, 37.50003, 127.00003, false\n2026-01-15T13:00:00, 37.50300, 127.00300, false\n2026-01-15T09:00:00, 37.50003, 127.00003, true";
  document.getElementById("n_arr").value="2026-01-15T09:00:00";
}
document.getElementById("n_gchk").addEventListener("change",e=>{document.getElementById("gbox").style.display=e.target.checked?"block":"none";});
