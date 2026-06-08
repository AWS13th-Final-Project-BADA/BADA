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
  if(h2) h2.innerHTML = gap>0 ? t("r_h2") : (wage.computable ? "확인된 금액 차이는<br>없었어요" : "차액 계산에<br>자료가 더 필요해요");
  document.getElementById("r_summary").textContent=narr.summary||"(요약을 생성하지 못했습니다)";
  document.getElementById("r_cmp_tbl").innerHTML=
    `<tr><td>${t("cmp_expected")}</td><td>${won(wage.expected)}</td></tr>`+
    `<tr><td>${t("cmp_received")}</td><td>${won(wage.received)}</td></tr>`+
    `<tr><td>${t("cmp_suspected")}</td><td style="color:var(--blue)">${won(wage.suspected_unpaid)}</td></tr>`;
  // 검증 포인트
  const cmp=a.comparisons||[];
  document.getElementById("r_cmp_pts").innerHTML=cmp.length?cmp.map(c=>{
    const st=c.status==="match"?'<span class="tag" style="background:#e8fbf3;color:#047857">일치</span>'
      :c.status==="mismatch"?'<span class="tag" style="background:#fef2f2;color:#b91c1c">차이</span>'
      :'<span class="tag">자료 부족</span>';
    const vals=Object.entries(c.values||{}).map(([k,v])=>k+" "+(typeof v==="number"?Number(v).toLocaleString():(v==null?"-":v))).join(" · ");
    return `<div style="padding:8px 0;border-bottom:1px solid var(--line)"><div style="font-size:13px;font-weight:700">${_esc(c.label)} ${st}</div><div class="small-muted">${_esc(vals)}</div>${c.note?`<div class="need">${_esc(c.note)}</div>`:""}</div>`;
  }).join(""):'<p class="small-muted" style="margin:0">대조할 자료가 부족해요. 명세서·통장·계약서를 함께 올리면 자동으로 비교돼요.</p>';
  // 법정 기준 점검
  const lf=legal.findings||[], mw=legal.min_wage||{};
  document.getElementById("r_legal").innerHTML=lf.length?lf.map(f=>{
    const col=f.severity==="high"?"#b91c1c":"#b45309";
    const ic=(f.type==="minimum_wage"||f.type==="minimum_wage_paid")?'<i class="ti ti-alert-triangle"></i>':(f.type==="premium_pay"?'<i class="ti ti-clock"></i>':'<i class="ti ti-receipt"></i>');
    return `<div style="padding:8px 0;border-bottom:1px solid var(--line)"><div style="font-size:13px;font-weight:700;color:${col}">${ic} ${_esc(f.message)}</div></div>`;
  }).join(""):`<p class="small-muted" style="margin:0">최저임금 미달·가산수당·과다공제로 확인된 항목은 없어요. (${mw.year||""}년 최저임금 ${won(mw.hourly)} 기준)</p>`;
  document.getElementById("r_ded_tbl").innerHTML=(a.deductions||[]).map(d=>{
    const srcs=(d.sources||[]).length?` · ${(d.sources||[]).join("/")}`:"";
    return `<tr><td>${_esc(d.name)} <span class="need">${_esc(d.category)}${srcs} · ${t("need")}</span></td><td>${won(d.amount)}</td></tr>`;
  }).join("")||`<tr><td>-</td><td>-</td></tr>`;
  const g=a.gps;
  document.getElementById("r_gps").innerHTML=g
    ?`<p style="margin:0;font-size:14px">핑 ${g.tagged_count}건 · 카톡-근무지 교차일치 <b>${g.cross_matches}건</b> <span class="need">조작 핑 자동 배제</span></p>`
    :`<p class="small-muted" style="margin:0">GPS 데이터 없음</p>`;
  document.getElementById("r_tl").innerHTML=(a.timeline||[]).map(e=>
    `<div class="timeline-item"><strong>${e.date||"-"}</strong><p>${_esc(e.text)}`
    +(e.confidence==="low"?' <span class="need">확인 필요</span>':"")
    +(e.source_evidence_id?' <span class="small-muted">· 출처 첨부</span>':"")
    +`</p></div>`).join("")||`<div class="timeline-item"><p>날짜 정보 부족</p></div>`;
  document.getElementById("r_miss").innerHTML=(a.missing||[]).map(m=>`<li>${_esc(m.reason)}</li>`).join("")||"<li>충분합니다.</li>";
}
function openReport(){ if(S.caseId)window.open(apiUrl("/cases/"+S.caseId+"/report.html"),"_blank"); }
