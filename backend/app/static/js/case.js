// ===== 사건 생성 (프론트/기획 소유) =====
const ISSUES={wage_unpaid:"임금체불",statement_mismatch:"명세서 불일치",deduction:"공제",overtime:"초과근무",no_contract:"계약서 미교부"};
function startNewCase(){
  const iss=document.getElementById("f_iss");
  if(!iss.children.length){
    Object.entries(ISSUES).forEach(([k,v])=>{const c=document.createElement("div");c.className="chip-sel";c.dataset.v=k;c.textContent=v;
      c.onclick=()=>c.classList.toggle("on");iss.appendChild(c);});
  }
  goPage("newcase",1);
}

async function submitCase(){
  const issue_types=[...document.querySelectorAll("#f_iss .chip-sel.on")].map(c=>c.dataset.v);
  const payload={workplace_name:document.getElementById("f_wn").value||"사업장",
    work_start_date:document.getElementById("f_ws").value||null,
    work_end_date:document.getElementById("f_we").value||null,
    agreed_hourly_wage:parseInt(document.getElementById("f_hw").value)||null,
    agreed_weekly_hours:parseFloat(document.getElementById("f_wh").value)||null,issue_types};
  try{const res=await api("POST","/cases",payload);S.caseId=res.id;S.analysis=null;buildUpload();goPage("upload",1);}
  catch(e){alert("사건 생성 실패: "+e.message);}
}

// 업로드 전 이미지 전처리: EXIF 회전 보정 + 다운스케일 + JPEG 재인코딩(용량↓, 인식 안정).
// 반환: {blob, name, warn}  warn=해상도 낮음 등 품질 경고(없으면 null). PDF/실패 시 원본 그대로.
