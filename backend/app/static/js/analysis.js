// ===== 분석·결과·법정점검 렌더 (OCR/분석 소유) =====
const lines=s=>(s||"").split("\n").map(x=>x.trim()).filter(Boolean);
function buildReq(){
  const hours=(document.getElementById("n_hrs").value||"").split(",").map(s=>parseFloat(s.trim())).filter(x=>!isNaN(x));
  const deposits=lines(document.getElementById("n_dep").value).map(l=>{const p=l.split(",");return{date:(p[0]||"").trim()||null,amount:parseInt((p[1]||"").replace(/[^0-9]/g,""))||0};});
  const deductions=lines(document.getElementById("n_ded").value).map(l=>{const p=l.split(",");return{name:(p[0]||"").trim(),amount:parseInt((p[1]||"").replace(/[^0-9]/g,""))||0};});
  const req={worked_hours:hours,deposits,deductions};
  const hw=parseInt(document.getElementById("n_hw").value); if(hw) req.agreed_hourly_wage=hw;
  if(document.getElementById("n_gchk").checked){
    const w=(document.getElementById("n_wp").value||"").split(",").map(s=>s.trim());
    if(w[0])req.workplace={lat:parseFloat(w[0]),lng:parseFloat(w[1]),radius_m:parseInt(w[2])||50};
    req.gps_logs=lines(document.getElementById("n_png").value).map(l=>{const p=l.split(",").map(s=>s.trim());return{ts:p[0],lat:parseFloat(p[1]),lng:parseFloat(p[2]),is_mocked:(p[3]||"").toLowerCase()==="true"};});
    req.chat_arrivals=lines(document.getElementById("n_arr").value);
  }
  return req;
}

function startAnalysis(){
  if(!S.caseId){alert("먼저 사건을 만들어주세요.");return;}
  setFlowStep(4);
  goPage("analyze",1);
  const fill=document.getElementById("barFill"),pct=document.getElementById("percentText"),txt=document.getElementById("progressText");
  const steps=[1,2,3,4].map(i=>document.getElementById("step"+i));
  const msgs=[t("an_p1"),t("an_s2"),t("an_s3"),t("an_s4")];
  const setStep=k=>steps.forEach((s,i)=>s.classList.toggle("active",i===k));
  let v=0,done=false;
  fill.style.width="0%";pct.textContent="0%";setStep(0);
  // 실제 분석 요청 — 응답이 오면 done 플래그(진행바 완료는 이 시점에 종속)
  const apiP=api("POST","/cases/"+S.caseId+"/analyze?lang="+S.lang,buildReq())
    .then(a=>{done=true;return a;})
    .catch(e=>{done=true;return {__err:e.message};});
  const timer=setInterval(async()=>{
    // 응답 전엔 90%까지만 점점 느리게(=실제 진행 중 표시), 응답 오면 빠르게 100%로
    v += done ? (100-v)*0.5 : Math.max(0.6,(90-v)*0.12);
    if(!done&&v>90)v=90;
    const shown=Math.min(Math.round(v),100);
    fill.style.width=shown+"%";pct.textContent=shown+"%";
    if(shown>=25&&shown<50){setStep(1);txt.textContent=msgs[1];}
    else if(shown>=50&&shown<75){setStep(2);txt.textContent=msgs[2];}
    else if(shown>=75){setStep(3);txt.textContent=msgs[3];}
    if(done&&shown>=100){
      clearInterval(timer);
      const a=await apiP;
      if(a&&a.__err){alert("분석 실패: "+a.__err);goPage("upload",1);return;}
      S.analysis=a;renderResult();goPage("result",2);
    }
  },120);
}

function renderResult(){
  const a=S.analysis;                 // 표준 AnalysisReport 스키마
  const wage=a.wage||{}, legal=a.legal||{}, narr=a.narrative||{};
  document.getElementById("r_money").textContent=won(wage.suspected_unpaid);
  // 차이가 없으면 헤드라인을 상황에 맞게(과장 금지)
  const gap=Number(wage.suspected_unpaid||0);
  const h2=document.querySelector('#result .result-hero h2');
  if(h2) h2.innerHTML = gap>0 ? t("r_h2") : (wage.computable ? t("r_h2_none") : t("r_h2_nodata"));
  document.getElementById("r_summary").textContent=narr.summary||t("no_summary");
  // summary가 면책 고지(한국어)를 포함하면 translations의 번역된 disclaimer로 교체
  const _discTr=(a.translations||[]).find(p=>p.related_issue==="disclaimer");
  if(_discTr && narr.summary && narr.summary.includes("법률자문")){
    document.getElementById("r_summary").textContent=_discTr.translated_text;
  }
  document.getElementById("r_cmp_tbl").innerHTML=
    `<tr><td>${t("cmp_expected")}</td><td>${won(wage.expected)}</td></tr>`+
    `<tr><td>${t("cmp_received")}</td><td>${won(wage.received)}</td></tr>`+
    `<tr><td>${t("cmp_suspected")}</td><td style="color:var(--blue)">${won(wage.suspected_unpaid)}</td></tr>`;
  // 검증 포인트
  const cmp=a.comparisons||[];
  document.getElementById("r_cmp_pts").innerHTML=cmp.length?cmp.map(c=>{
    const st=c.status==="match"?`<span class="tag" style="background:#e8fbf3;color:#047857">${t("cmp_match")}</span>`
      :c.status==="mismatch"?`<span class="tag" style="background:#fef2f2;color:#b91c1c">${t("cmp_mismatch")}</span>`
      :`<span class="tag">${t("cmp_nodata")}</span>`;
    const vals=Object.entries(c.values||{}).map(([k,v])=>k+" "+(typeof v==="number"?Number(v).toLocaleString():(v==null?"-":v))).join(" · ");
    return `<div style="padding:8px 0;border-bottom:1px solid var(--line)"><div style="font-size:13px;font-weight:700">${_esc(c.label)} ${st}</div><div class="small-muted">${_esc(vals)}</div>${c.note?`<div class="need">${_esc(c.note)}</div>`:""}</div>`;
  }).join(""):`<p class="small-muted" style="margin:0">${t("cmp_empty")}</p>`;
  // 법정 기준 점검
  const lf=legal.findings||[], mw=legal.min_wage||{};
  document.getElementById("r_legal").innerHTML=lf.length?lf.map(f=>{
    const col=f.severity==="high"?"#b91c1c":"#b45309";
    const ic=(f.type==="minimum_wage"||f.type==="minimum_wage_paid")?'<i class="ti ti-alert-triangle"></i>':(f.type==="premium_pay"?'<i class="ti ti-clock"></i>':'<i class="ti ti-receipt"></i>');
    return `<div style="padding:8px 0;border-bottom:1px solid var(--line)"><div style="font-size:13px;font-weight:700;color:${col}">${ic} ${_esc(f.message)}</div></div>`;
  }).join(""):`<p class="small-muted" style="margin:0">${t("legal_ok")} (${mw.year||""} ${won(mw.hourly)})</p>`;
  document.getElementById("r_ded_tbl").innerHTML=(a.deductions||[]).map(d=>{
    const srcs=(d.sources||[]).length?` · ${(d.sources||[]).join("/")}`:"";
    return `<tr><td>${_esc(d.name)} <span class="need">${_esc(d.category)}${srcs} · ${t("need")}</span></td><td>${won(d.amount)}</td></tr>`;
  }).join("")||`<tr><td>-</td><td>-</td></tr>`;
  const g=a.gps;
  document.getElementById("r_gps").innerHTML=g
    ?`<p style="margin:0;font-size:14px">${t("gps_pings")} ${g.tagged_count} · ${t("gps_cross")} <b>${g.cross_matches}</b> <span class="need">${t("gps_mocked_excluded")}</span></p>`
    :`<p class="small-muted" style="margin:0">${t("gps_none")}</p>`;

  // 카카오맵 GPS 핑 시각화
  if (g && typeof renderGpsMap === 'function') {
    const req = buildReq();
    const wp = req.workplace;
    const pings = (req.gps_logs || []).map(function(p) {
      return { lat: p.lat, lng: p.lng, ts: p.ts,
               status: p.is_mocked ? null : null }; // status는 서버 응답에서 오면 더 정확
    });
    if (wp && pings.length > 0) {
      // 분석 결과에 tagged_logs가 있으면 status 사용, 없으면 입력값 그대로
      const taggedLogs = a.tagged_gps_logs || pings;
      setTimeout(function() {
        renderGpsMap(wp.lat, wp.lng, wp.radius_m || 50, taggedLogs);
      }, 200);
    }
  }
  document.getElementById("r_tl").innerHTML=(a.timeline||[]).map(e=>
    `<div class="timeline-item"><strong>${e.date||"-"}</strong><p>${_esc(e.text)}`
    +(e.confidence==="low"?` <span class="need">${t("need")}</span>`:"")
    +(e.source_evidence_id?` <span class="small-muted">· ${t("src_attached")}</span>`:"")
    +`</p></div>`).join("")||`<div class="timeline-item"><p>${t("no_date_info")}</p></div>`;
  document.getElementById("r_miss").innerHTML=(a.missing||[]).map(m=>{
    // translations에서 번역된 누락 안내 찾기
    const tp=(a.translations||[]).find(p=>p.related_issue==="missing_evidence"&&p.source_text&&p.source_text.includes(m.item));
    const text=tp?tp.translated_text:_esc(m.reason);
    return `<li>${text}</li>`;
  }).join("")||`<li>${t("enough")}</li>`;
  // 면책 고지: translations의 disclaimer 번역으로 갱신 (applyLang 이후에도 유지)
  const _dp=(a.translations||[]).find(p=>p.related_issue==="disclaimer");
  if(_dp){const _el=document.querySelector('[data-k="r_disc"]');if(_el)_el.textContent=_dp.translated_text;}
}
function openReport(){ if(S.caseId)window.open(apiUrl("/cases/"+S.caseId+"/report.html?lang="+S.lang),"_blank"); }
