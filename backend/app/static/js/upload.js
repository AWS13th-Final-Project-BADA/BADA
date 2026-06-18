// ===== 업로드·촬영·OCR 추출·편집 (OCR 담당 소유) =====
const ROWS=[
 {cat:"contract",icon:'<i class="ti ti-file-text"></i>',bg:"soft-blue",tk:"up_contract",sk:"up_contract_desc"},
 {cat:"statement",icon:'<i class="ti ti-receipt"></i>',bg:"soft-green",tk:"up_statement",sk:"up_statement_desc"},
 {cat:"payment",icon:'<i class="ti ti-building-bank"></i>',bg:"soft-orange",tk:"up_payment",sk:"up_payment_desc"},
 {cat:"chat",icon:'<i class="ti ti-message"></i>',bg:"soft-blue",tk:"up_chat",sk:"up_chat_desc"},
 {cat:"other",icon:'<i class="ti ti-world"></i>',bg:"soft-green",tk:"up_other",sk:"up_other_desc"},
 {cat:"audio",icon:'<i class="ti ti-microphone"></i>',bg:"soft-orange",tk:"up_audio",sk:"up_audio_desc"}
];


async function preprocessImage(file){
  if(!file.type.startsWith("image/")) return {blob:file,name:file.name,warn:null};
  try{
    const bmp=await createImageBitmap(file,{imageOrientation:"from-image"});
    const MAX=1568, scale=Math.min(1,MAX/Math.max(bmp.width,bmp.height));  // Claude 비전 권장 긴변(>1568은 내부 축소 → 이득無)
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
    const res=await fetch(apiUrl("/cases/"+S.caseId+"/evidences/upload"),{method:"POST",body:fd});
    if(!res.ok) throw new Error(await res.text());
    btn.innerHTML='<i class="ti ti-check"></i>완료'; btn.classList.add("done");
  }catch(e){ btn.textContent="다시"; alert("업로드 실패: "+e.message); }
}

// 여러 장을 category='auto'로 올림 → 서버가 분류·선별. 다 올리면 자동 추출 시작.
async function doUploadAuto(files, st, warnEl){
  let ok=0;
  for(let i=0;i<files.length;i++){
    st.innerHTML='<i class="ti ti-loader-2"></i> 올리는 중 '+(i+1)+'/'+files.length;
    try{
      const {blob,name}=await preprocessImage(files[i]);
      const fd=new FormData(); fd.append("category","auto"); fd.append("file",blob,name);
      const res=await fetch(apiUrl("/cases/"+S.caseId+"/evidences/upload"),{method:"POST",body:fd});
      if(res.ok) ok++;
    }catch(e){}
  }
  st.innerHTML='<i class="ti ti-check"></i> '+ok+'장 업로드 완료';
  if(warnEl) warnEl.textContent="에이전트가 종류를 분류하고 무관한 건 빼요. 결과는 아래에서 확인·수정하세요.";
  if(typeof runExtract==="function") runExtract();   // 자동으로 분류·추출 시작
}

// 제외된 자료 되살리기(HITL 안전망) → 재추출
async function restoreEvidence(eid){
  try{
    await api("POST","/cases/"+S.caseId+"/evidences/"+eid+"/restore",{category:"other"});
    if(typeof runExtract==="function") runExtract();
  }catch(e){ alert("되살리기 실패: "+e.message); }
}

// 자동 분류 근거 한 줄(있을 때만)
function _classifyNote(cl){
  if(!cl) return "";
  const conf={high:"확실",medium:"아마 맞아요",low:"불확실 — 확인해주세요"}[cl.confidence]||"";
  const why=cl.reason?(" — "+_esc(cl.reason)):"";
  return `<div class="small-muted" style="margin-top:4px"><i class="ti ti-sparkles"></i> 자동분류: ${_esc(_catLabel(cl.category))} <b>(${conf})</b>${why}</div>`;
}

function buildUpload(){
  const c=document.getElementById("uploadCard");
  c.className="up-grid"; c.innerHTML="";
  // 자동 분류 카드 — 여러 장을 한 번에 던지면 에이전트가 종류를 알아서 판단
  const auto=document.createElement("div"); auto.className="up-card";
  auto.style="grid-column:1/-1;border:1px dashed #93c5fd;background:#f5f9ff";
  auto.innerHTML=`<div class="file-icon soft-blue"><i class="ti ti-sparkles"></i></div>
    <strong>여러 장 한 번에</strong>
    <span class="up-state"><i class="ti ti-folder"></i> 자동 분류 업로드</span>
    <span class="need"></span>
    <input type="file" accept="image/*,application/pdf" multiple class="i-auto" style="display:none">`;
  const ainp=auto.querySelector(".i-auto"), ast=auto.querySelector(".up-state"), awarn=auto.querySelector(".need");
  auto.onclick=(e)=>{ if(e.target.tagName!=="INPUT") ainp.click(); };
  ainp.onchange=()=>{ if(ainp.files.length) doUploadAuto([...ainp.files], ast, awarn); };
  c.appendChild(auto);
  // 폴더 통째로 선택 — 폴더 안 이미지/PDF 전부 자동 분류
  const folder=document.createElement("div"); folder.className="up-card";
  folder.style="grid-column:1/-1;border:1px dashed #93c5fd;background:#f5f9ff";
  folder.innerHTML=`<div class="file-icon soft-blue"><i class="ti ti-folder-open"></i></div>
    <strong>폴더 통째로</strong>
    <span class="up-state"><i class="ti ti-folders"></i> 폴더 선택 → 자동 분류</span>
    <span class="need"></span>
    <input type="file" webkitdirectory directory multiple class="i-folder" style="display:none">`;
  const finp=folder.querySelector(".i-folder"), fst=folder.querySelector(".up-state"), fwarn=folder.querySelector(".need");
  folder.onclick=(e)=>{ if(e.target.tagName!=="INPUT") finp.click(); };
  finp.onchange=()=>{
    // 폴더 안에서 이미지/PDF만 골라냄(잡파일 제외)
    const files=[...finp.files].filter(f=>/\.(png|jpe?g|webp|heic|pdf)$/i.test(f.name));
    if(files.length) doUploadAuto(files, fst, fwarn);
    else fst.innerHTML='<i class="ti ti-alert-circle"></i> 이미지/PDF가 없어요';
  };
  c.appendChild(folder);
  ROWS.forEach(r=>{
    const card=document.createElement("div"); card.className="up-card";
    card.innerHTML=`<div class="file-icon ${r.bg}">${r.icon}</div>
      <strong>${t(r.tk)}</strong>
      <span class="up-state"><i class="ti ti-camera"></i> ${t("up_shoot_file")}</span>
      <span class="need"></span>
      <input type="file" accept="image/*,application/pdf" class="i-up" style="display:none">`;
    const inp=card.querySelector(".i-up"), st=card.querySelector(".up-state"), warnEl=card.querySelector(".need");
    if(r.cat==="audio"){ inp.accept="audio/*,.mp3,.mp4,.m4a,.wav,.flac,.ogg,.amr,.webm"; inp.multiple=true; }
    card.onclick=(e)=>{ if(e.target.tagName!=="INPUT") inp.click(); };
    inp.onchange=async()=>{
      if(!inp.files.length) return;
      const files=[...inp.files];
      for(let i=0;i<files.length;i++){
        st.innerHTML=files.length>1?`<i class="ti ti-loader"></i> ${i+1}/${files.length} 업로드 중...`:"업로드 중...";
        await doUpload(r.cat, files[i], st, warnEl);
      }
      if(files.length>1){ st.innerHTML='<i class="ti ti-check"></i> '+files.length+'개 완료'; st.classList.add("done"); }
    };
    c.appendChild(card);
  });
}

const _esc=(s)=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
const _catLabel=(c)=>{const r=ROWS.find(x=>x.cat===c);return r?t(r.tk):c;};
const _won=(n)=>Number(n).toLocaleString()+"원";

function renderSanity(items){
  return items.map(s=>`<div style="margin-top:8px;padding:8px 10px;background:#fff7ed;border-radius:8px;border-left:3px solid #f59e0b">
    <div style="font-size:12px;font-weight:700;color:#b45309"><i class="ti ti-alert-triangle"></i> ${_esc(s.field)} 값 확인 필요</div>
    <div class="small-muted">${_esc(s.note)}</div></div>`).join("");
}
function renderQuality(q){
  const color={high:"#047857",medium:"#b45309",low:"#b91c1c"}[q.level]||"#6b7280";
  const lvl={high:"증거력 높음",medium:"증거력 보통",low:"증거력 낮음"}[q.level]||q.level;
  const chk=Object.entries(q.checklist||{}).map(([k,v])=>`<span class="tag" style="background:${v?'#e8fbf3':'#f3f4f6'};color:${v?'#047857':'#9ca3af'}">${v?'<i class=\'ti ti-check\'></i>':'<i class=\'ti ti-point\'></i>'} ${k}</span>`).join(" ");
  const warn=(q.warnings||[]).map(w=>`<div class="need" style="font-weight:600"><i class="ti ti-alert-triangle"></i> ${_esc(w)}</div>`).join("");
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
    const msg = e.file_type==="audio" ? "⏳ 음성을 텍스트로 변환 중입니다" : "⏳ 읽는 중...";
    return "<p class='small-muted'>"+msg+"</p>";
  }
  if(e.ocr_status!=="done"){
    return "<p class='small-muted'>"+_esc(e.error||e.ocr_text||"읽기 실패")+"</p>"+
      "<button class='upload-chip' style='margin-top:8px' onclick=\"runExtract()\">다시 시도</button>";
  }
  // Audio transcription result with speaker diarization
  if(e.file_type==="audio" && e.ocr_text){
    const formatted = e.ocr_text.split("\n").map(line => {
      const m = line.match(/^(Speaker \d+): (.+)$/);
      if(m) return `<div class="speaker-line"><span class="speaker-label">${m[1]}</span> ${_esc(m[2])}</div>`;
      return `<p>${_esc(line)}</p>`;
    }).join("");
    return `<div class="transcript-result">${formatted}</div>`;
  }
  const en=e.entities||{}, eid=e.evidence_id, cm=_confMap(e);
  S.ext[eid]=en;
  // 금액 편집 행 (저신뢰는 노랑 강조)
  const amts=(en.amounts||[]).map((a,i)=>{
    const lv=cm[a.label]||"medium";
    return `<div class="amt-row" style="display:flex;gap:6px;margin-top:5px;align-items:center">
      <input class="amt-label" value="${_esc(a.label||"")}" placeholder="항목" style="flex:1.2;padding:8px 9px"/>
      <input class="amt-val" type="number" value="${a.value==null?"":a.value}" placeholder="금액" style="flex:1;padding:8px 9px;${_lowStyle(lv)}"/>
      ${lv==="low"?'<span title="확인 필요" style="color:#9a6700"><i class="ti ti-alert-triangle"></i></span>':''}</div>`;
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
    <button class="primary-btn" style="margin-top:12px;padding:11px" onclick="saveEntities('${eid}')"><i class="ti ti-edit"></i> 수정 저장</button>
    <span id="save_${eid}" class="small-muted" style="margin-left:8px"></span>
    ${e.evidence_quality?renderQuality(e.evidence_quality):""}
    ${e.sanity&&e.sanity.length?renderSanity(e.sanity):""}
    ${e.ocr_text?"<details style='margin-top:6px'><summary class='small-muted' style='cursor:pointer'>읽은 원문 보기</summary><pre style='white-space:pre-wrap;font-size:12px;color:#374151;background:#f8fafc;padding:8px;border-radius:8px;max-height:180px;overflow:auto'>"+_esc(e.ocr_text)+"</pre></details>":""}
  </div>`;
}

function renderCard(e){
  // 자동 분류로 '제외'된 자료 — 이유 + 되살리기(안전망)
  if(e.ocr_status==="excluded"){
    const cl=e.classify||{};
    return `<div class="card" id="card_${e.evidence_id}" style="margin:8px 0;padding:14px;opacity:.85">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <strong style="font-size:13px"><i class="ti ti-photo-off"></i> ${_esc(e.file_name||"")}</strong>
        <span class='tag' style='background:#f3f4f6;color:#6b7280'>제외</span></div>
      <p class="small-muted" style="margin-top:6px">${_esc(cl.reason||e.ocr_text||"임금체불과 무관한 자료로 보여서 뺐어요")}</p>
      <button class="upload-chip" style="margin-top:8px" onclick="restoreEvidence('${e.evidence_id}')"><i class="ti ti-arrow-back-up"></i> 되살리기</button>
    </div>`;
  }
  const badge = e.ocr_status==="done"
    ? "<span class='tag' style='background:#e8fbf3;color:#047857'>읽음</span>"
    : (e.ocr_status==="processing"||e.ocr_status==="pending")
      ? "<span class='tag' style='background:#eef2ff;color:#2563eb'>읽는 중</span>"
      : "<span class='tag' style='background:#fef2f2;color:#b91c1c'>실패</span>";
  return `<div class="card" id="card_${e.evidence_id}" style="margin:8px 0;padding:14px">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
      <strong style="font-size:13px">${_esc(e.file_name||"")} <span class='tag'>${_esc(_catLabel(e.category))}</span></strong>${badge}</div>
    ${_classifyNote(e.classify)}
    ${renderCardBody(e)}</div>`;
}

function renderExtract(r){
  const ev=r.evidences||[];
  if(!ev.length) return "";
  return "<h3 style='margin:14px 0 6px'><i class='ti ti-eye'></i> AI가 읽은 내용 <span class='small-muted' style='font-weight:400'>· 값을 직접 고칠 수 있어요</span></h3>"+ev.map(renderCard).join("");
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


// ===== 증거 수집 에이전트 — 추천 카드 UI (에이전트 담당 소유) =====

/**
 * 에이전트 스캔 실행: 선택한 파일들을 /scan에 보내 후보를 받아옴(OCR X, 분류만).
 * 결과를 추천 카드로 렌더, 사용자가 체크/승인하면 agent-upload로 등록.
 */
async function agentScan(files) {
  if (!S.caseId) { alert("먼저 사건을 만들어주세요."); return; }
  const container = document.getElementById("agentRecommend");
  if (!container) return;
  container.innerHTML = '<p class="small-muted"><i class="ti ti-loader-2 spin"></i> 에이전트가 증거를 찾고 있어요...</p>';

  const fd = new FormData();
  for (const f of files) {
    const { blob, name } = await preprocessImage(f);
    fd.append("files", blob, name);
  }

  try {
    const res = await fetch(apiUrl("/cases/" + S.caseId + "/evidences/scan"), { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    _renderAgentCards(container, data, files);
  } catch (e) {
    container.innerHTML = '<p class="small-muted" style="color:#b91c1c">스캔 실패: ' + _esc(e.message) + '</p>';
  }
}

function _renderAgentCards(container, data, originalFiles) {
  const { candidates, summary, recommended } = data;
  if (!candidates || !candidates.length) {
    container.innerHTML = '<p class="small-muted">증거로 쓸 만한 파일을 못 찾았어요.</p>';
    return;
  }

  const recCount = recommended.length;
  const rejCount = summary.rejected || 0;

  let html = `<div style="margin:12px 0 8px;padding:10px 14px;background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0">
    <strong style="font-size:13px"><i class="ti ti-sparkles"></i> 에이전트 추천</strong>
    <span class="small-muted" style="margin-left:8px">${recCount}장 추천 · ${rejCount}장 제외</span>
  </div>`;

  html += '<div id="agentCandidates" style="display:flex;flex-direction:column;gap:8px">';
  for (const c of candidates) {
    const isRec = c.decision !== "rejected";
    const icon = isRec ? (c.decision === "auto_accept" ? "ti-check-circle" : "ti-help-circle") : "ti-circle-x";
    const color = isRec ? (c.decision === "auto_accept" ? "#047857" : "#b45309") : "#6b7280";
    const label = c.decision === "auto_accept" ? "추천" : c.decision === "needs_review" ? "확인 필요" : "제외";
    const checked = isRec ? "checked" : "";
    const opacity = isRec ? "1" : "0.5";

    html += `<label style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;cursor:pointer;opacity:${opacity}">
      <input type="checkbox" class="agent-chk" data-fn="${_esc(c.file_name)}" ${checked} style="margin-top:3px;width:18px;height:18px"/>
      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:center;gap:6px">
          <i class="ti ${icon}" style="color:${color}"></i>
          <strong style="font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${_esc(c.file_name)}</strong>
          <span class="tag" style="font-size:11px;background:#f3f4f6">${_esc(label)}</span>
        </div>
        <div class="small-muted" style="margin-top:4px">${(c.reasons || []).map(r => _esc(r)).join(" · ")}</div>
      </div>
    </label>`;
  }
  html += '</div>';

  html += `<div style="margin-top:12px;display:flex;gap:8px">
    <button class="primary-btn" style="flex:1;padding:12px" onclick="_agentApprove()">
      <i class="ti ti-upload"></i> 선택한 파일 등록
    </button>
    <button class="upload-chip" style="padding:12px" onclick="document.getElementById('agentRecommend').innerHTML=''">
      취소
    </button>
  </div>`;

  container.innerHTML = html;

  // 원본 파일을 나중에 업로드할 때 쓸 수 있게 보관
  container._originalFiles = originalFiles;
}

async function _agentApprove() {
  const container = document.getElementById("agentRecommend");
  if (!container) return;
  const checks = container.querySelectorAll(".agent-chk:checked");
  if (!checks.length) { toast("등록할 파일을 선택해주세요."); return; }

  const selectedNames = new Set([...checks].map(c => c.dataset.fn));
  const originalFiles = container._originalFiles || [];

  // 선택된 이름에 해당하는 원본 파일만 골라 agent-upload로 전송
  const filesToUpload = originalFiles.filter(f => selectedNames.has(f.name));
  if (!filesToUpload.length) {
    // 원본이 없으면(이미 해제됨) 이름만으로 category=auto 업로드
    toast("파일을 다시 선택해주세요.");
    return;
  }

  container.innerHTML = '<p class="small-muted"><i class="ti ti-loader-2 spin"></i> 등록 중...</p>';

  try {
    const fd = new FormData();
    for (const f of filesToUpload) {
      const { blob, name } = await preprocessImage(f);
      fd.append("files", blob, name);
    }
    const res = await fetch(apiUrl("/cases/" + S.caseId + "/evidences/agent-upload"), { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const result = await res.json();

    container.innerHTML = `<div style="padding:12px 14px;background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0">
      <strong><i class="ti ti-check"></i> ${result.uploaded}장 등록 완료</strong>
      <p class="small-muted" style="margin-top:4px">자동으로 분류·OCR이 시작됩니다.</p>
    </div>`;

    // 등록 후 자동으로 extract 시작
    if (typeof runExtract === "function") runExtract();
  } catch (e) {
    container.innerHTML = '<p class="small-muted" style="color:#b91c1c">등록 실패: ' + _esc(e.message) + '</p>';
  }
}

// buildUpload에 에이전트 스캔 카드 추가 (기존 buildUpload 후 호출)
function _injectAgentScanCard() {
  const c = document.getElementById("uploadCard");
  if (!c) return;

  // 이미 있으면 중복 방지
  if (document.getElementById("agentScanCard")) return;

  const card = document.createElement("div");
  card.id = "agentScanCard";
  card.className = "up-card";
  card.style = "grid-column:1/-1;border:2px solid #a78bfa;background:#faf5ff";
  card.innerHTML = `<div class="file-icon" style="background:#f3e8ff"><i class="ti ti-robot" style="color:#7c3aed"></i></div>
    <strong>에이전트 스캔</strong>
    <span class="up-state" id="agentScanState"><i class="ti ti-search"></i> 파일을 선택하면 증거를 찾아요</span>
    <input type="file" accept="image/*,application/pdf" multiple class="i-agent-scan" style="display:none">`;

  const inp = card.querySelector(".i-agent-scan");
  // 에이전트 스캔은 디바이스 파일을 읽으므로, 클릭 시 먼저 동의를 받는다(HITL + PIPA).
  card.onclick = (e) => {
    if (e.target.tagName === "INPUT") return;
    _agentConsent(() => inp.click());
  };
  inp.onchange = () => { if (inp.files.length) agentScan([...inp.files]); };

  // 맨 앞에 삽입
  c.insertBefore(card, c.firstChild);

  // 추천 결과 영역
  if (!document.getElementById("agentRecommend")) {
    const rec = document.createElement("div");
    rec.id = "agentRecommend";
    rec.style = "grid-column:1/-1";
    c.insertBefore(rec, card.nextSibling);
  }
}

// 기존 buildUpload를 래핑해서 에이전트 카드 주입
const _origBuildUpload = buildUpload;
buildUpload = function () {
  _origBuildUpload();
  _injectAgentScanCard();
};


/**
 * 에이전트 스캔 동의 모달 (PIPA / 최소수집 / HITL).
 * 디바이스 파일을 읽기 전 사용자 동의를 받는다. 동의 시 onAgree() 실행.
 * security.md의 동의 문구 기준 — "본인 자료만, 정리 목적, 민감정보 자동 가림, 법률자문 아님".
 */
function _agentConsent(onAgree) {
  // 이미 떠 있으면 중복 방지
  if (document.getElementById("agentConsentOverlay")) return;

  const overlay = document.createElement("div");
  overlay.id = "agentConsentOverlay";
  overlay.style = "position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;z-index:9999;padding:20px";

  overlay.innerHTML = `
    <div style="background:#fff;border-radius:16px;max-width:380px;width:100%;padding:22px;box-shadow:0 10px 40px rgba(0,0,0,.25)">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <div style="width:40px;height:40px;border-radius:10px;background:#f3e8ff;display:flex;align-items:center;justify-content:center">
          <i class="ti ti-shield-check" style="color:#7c3aed;font-size:22px"></i>
        </div>
        <strong style="font-size:16px">사진·파일 접근 동의</strong>
      </div>

      <p style="font-size:13px;color:#374151;line-height:1.6;margin:0 0 12px">
        에이전트가 증거가 될 만한 자료(급여명세서·계약서·통장·대화 캡처)를 찾기 위해
        선택한 사진·파일을 읽습니다.
      </p>

      <ul style="font-size:12px;color:#4b5563;line-height:1.7;margin:0 0 14px;padding-left:18px">
        <li><b>본인이 직접 참여한 대화·본인 자료만</b> 올려주세요.</li>
        <li>증거 정리 목적으로만 사용되며, 계좌·주민번호 등 민감정보는 자동으로 가립니다.</li>
        <li>추천된 자료는 <b>회원님이 확인·선택해야</b> 등록됩니다(자동 등록 안 함).</li>
        <li>본 도구는 법률자문이 아니라 상담 준비용 정리 도구입니다.</li>
      </ul>

      <label style="display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:14px;cursor:pointer">
        <input type="checkbox" id="agentConsentChk" style="width:18px;height:18px"/>
        위 내용에 동의합니다.
      </label>

      <div style="display:flex;gap:8px">
        <button id="agentConsentCancel" class="upload-chip" style="flex:1;padding:12px">취소</button>
        <button id="agentConsentOk" class="primary-btn" style="flex:1.5;padding:12px;opacity:.5" disabled>
          <i class="ti ti-search"></i> 동의하고 스캔
        </button>
      </div>
    </div>`;

  document.body.appendChild(overlay);

  const chk = overlay.querySelector("#agentConsentChk");
  const okBtn = overlay.querySelector("#agentConsentOk");
  const cancelBtn = overlay.querySelector("#agentConsentCancel");
  const close = () => overlay.remove();

  // 체크해야 동의 버튼 활성화
  chk.onchange = () => {
    okBtn.disabled = !chk.checked;
    okBtn.style.opacity = chk.checked ? "1" : ".5";
  };
  cancelBtn.onclick = close;
  // 바깥 클릭 시 닫기
  overlay.onclick = (e) => { if (e.target === overlay) close(); };
  okBtn.onclick = () => {
    if (!chk.checked) return;
    close();
    onAgree();
  };
}
