// ===== AI 안내 챗봇 (AI 담당 소유) =====
function renderChat(){
  const list=document.getElementById("chatList");
  if(!S.chat.length){
    list.classList.add("empty");
    list.innerHTML=`<div class="chat-bubble bot">${esc(ct("empty"))}</div>`;
    return;
  }
  list.classList.remove("empty");
  list.innerHTML=S.chat.map(m=>{
    if(m.role==="user")return `<div class="chat-bubble user">${esc(m.text)}</div>`;
    const meta=m.meta?`<div class="chat-meta">
      <span>${esc(m.meta.ai_provider||"unknown")}</span><span>${esc(m.meta.intent)}</span><span>${esc(m.meta.risk_level)}</span><span>fallback ${m.meta.fallback_used?"on":"off"}</span>
    </div>`:"";
    const next=(m.next_actions||[]).length?`<ul class="next-actions">${m.next_actions.map(a=>`<li>${esc(a)}</li>`).join("")}</ul>`:"";
    const sources=(m.sources||[]).length?`<ul class="rag-sources">${m.sources.map(s=>`<li>${esc(s.source_org)} · ${esc(s.title)}${s.section?" · "+esc(s.section):""}</li>`).join("")}</ul>`:"";
    const disclaimer=m.disclaimer?`<div class="chat-disclaimer">${esc(m.disclaimer)}</div>`:"";
    return `<div class="chat-bubble bot">${esc(m.text)}${meta}${next}${sources}${disclaimer}</div>`;
  }).join("");
  list.scrollIntoView({block:"end"});
}

function askQuickChat(message){
  const input=document.getElementById("chatInput");
  input.value=message;
  sendChatMessage();
}

async function sendChatMessage(event){
  if(event)event.preventDefault();
  const input=document.getElementById("chatInput");
  const btn=document.getElementById("chatSendBtn");
  const message=input.value.trim();
  if(!message||btn.disabled)return;
  S.chat.push({role:"user",text:message});
  input.value="";
  renderChat();
  btn.disabled=true;
  S.chat.push({role:"bot",text:ct("loading")});
  renderChat();
  try{
    const res=await api("POST","/chat/messages",{case_id:S.caseId||1,message,language:S.lang});
    S.chat.pop();
    S.chat.push({role:"bot",text:res.answer,meta:res,next_actions:res.next_actions||[],sources:res.sources||[],disclaimer:res.disclaimer});
  }catch(e){
    S.chat.pop();
    S.chat.push({role:"bot",text:ct("error")});
  }finally{
    btn.disabled=false;
    renderChat();
    input.focus();
  }
}
