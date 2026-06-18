// Community feed
const COMMUNITY_CATEGORIES={
  all:"인기글",
  free:"자유",
  wage:"임금",
  petition:"진정서",
  review:"후기",
  mine:"내 글",
  translation:"번역",
  notice:"공지"
};
const COMMUNITY_LANG={ko:"한국어",vi:"Tiếng Việt",en:"English",id:"Indonesia",km:"ខ្មែរ",ne:"नेपाली",th:"ไทย",ja:"日本語"};

const COMMUNITY_TEXT={
  ko:{
    hero_label:"커뮤니티",hero_title:"궁금한 점을<br/>편하게 물어보세요",hero_body:"임금, 계약서, 공제, 진정서 준비처럼 혼자 정리하기 어려운 내용을 익명으로 묻고 답해요.",
    search_placeholder:"비슷한 상황 검색",search_empty:"검색 결과가 없어요.<br/>다른 단어로 다시 찾아보세요.",stat_posts:"게시글",stat_comments:"댓글",stat_saved:"저장",tab_all:"인기글",tab_free:"자유",tab_wage:"임금",tab_petition:"진정서",tab_review:"후기",tab_mine:"내 글",
    hot_title:"많이 본 글",refresh:"새로고침",me:"나",compose_entry:"익명으로 질문 남기기",nav_community:"커뮤니티",
    sheet_new:"익명 글쓰기",sheet_edit:"게시글 수정",close:"닫기",board_wage:"임금/공제",board_petition:"진정서",board_review:"상담 후기",board_free:"자유",
    title_placeholder:"제목을 입력하세요",content_placeholder:"상담 전 준비하고 싶은 내용을 적어주세요. 이름, 전화번호, 외국인등록번호는 올리지 않는 것이 안전해요.",
    safety_default:"게시 전 개인정보와 단정적인 표현을 확인합니다.",safety_edit:"수정한 내용도 안전하게 작성됐는지 확인합니다.",btn_safety:"안전검사",btn_post:"게시하기",btn_update:"수정하기",
    loading:"커뮤니티를 불러오는 중...",load_error:"커뮤니티를 불러오지 못했어요.<br/>서버 연결과 마이그레이션 상태를 확인해 주세요.",empty_feed:"아직 게시글이 없어요.<br/>첫 질문을 익명으로 남겨보세요.",empty_hot:"인기글이 아직 없어요.",
    edit:"수정",delete:"삭제",more_comments:"댓글 {count}개 모두 보기",consult_tag:"상담준비",comment_placeholder:"댓글 달기 · 번역 보기 지원",comment_submit:"게시",
    translate_view:"번역 보기",translate_hide:"번역 접기",translating:"번역 중...",translation_empty:"번역 결과가 비어 있어요.",translation_error:"번역을 가져오지 못했어요.",
    input_required:"내용을 먼저 입력해 주세요.",safety_checking:"AI가 표현을 확인하고 있어요...",suggested:"추천 표현",safety_failed:"안전검사를 완료하지 못했어요. 잠시 후 다시 시도해 주세요.",
    title_content_required:"제목과 내용을 2자 이상 입력해 주세요.",post_created:"커뮤니티에 게시했어요.",post_updated:"게시글을 수정했어요.",post_fail:"게시하지 못했어요. 개인정보나 법률 판단 표현을 확인해 주세요.",
    comment_fail:"댓글을 게시하지 못했어요. 표현을 조금 더 안전하게 바꿔 주세요.",comments_fail:"댓글을 불러오지 못했어요.",delete_post_confirm:"이 게시글을 삭제할까요? 댓글과 번역 보기에서도 더 이상 보이지 않아요.",post_deleted:"게시글을 삭제했어요.",post_delete_fail:"게시글을 삭제하지 못했어요.",
    edit_comment_prompt:"댓글 내용을 수정하세요.",comment_content_required:"댓글 내용을 입력해 주세요.",comment_updated:"댓글을 수정했어요.",comment_update_fail:"댓글을 수정하지 못했어요. 표현을 안전하게 바꿔 주세요.",delete_comment_confirm:"이 댓글을 삭제할까요?",comment_deleted:"댓글을 삭제했어요.",comment_delete_fail:"댓글을 삭제하지 못했어요.",
    reaction_fail:"반응을 저장하지 못했어요.",report_prompt:"신고 사유를 짧게 입력해 주세요.",report_done:"신고가 접수되었어요.",report_fail:"신고를 접수하지 못했어요.",
    just_now:"방금",min_ago:"{n}분 전",hour_ago:"{n}시간 전",day_ago:"{n}일 전",
    cat_all:"인기글",cat_free:"자유",cat_wage:"임금",cat_petition:"진정서",cat_review:"후기",cat_mine:"내 글",cat_translation:"번역",cat_notice:"공지"
  },
  en:{
    hero_label:"Community",hero_title:"Ask what you need<br/>before consultation",hero_body:"Ask anonymously about wages, contracts, deductions, complaint forms, and other preparation details.",
    search_placeholder:"Search similar cases",search_empty:"No matching posts.<br/>Try another keyword.",stat_posts:"Posts",stat_comments:"Comments",stat_saved:"Saved",tab_all:"Hot",tab_free:"Free",tab_wage:"Wage",tab_petition:"Complaint",tab_review:"Reviews",tab_mine:"Mine",
    hot_title:"Popular Posts",refresh:"Refresh",me:"Me",compose_entry:"Ask anonymously",nav_community:"Community",
    sheet_new:"Write Anonymously",sheet_edit:"Edit Post",close:"Close",board_wage:"Wage/Deduction",board_petition:"Complaint",board_review:"Consult Review",board_free:"Free",
    title_placeholder:"Enter a title",content_placeholder:"Write what you want to prepare before consultation. It is safer not to post names, phone numbers, or registration numbers.",
    safety_default:"Before posting, check for personal information and overly certain wording.",safety_edit:"Please check that the edited content is written safely.",btn_safety:"Safety Check",btn_post:"Post",btn_update:"Update",
    loading:"Loading community...",load_error:"Could not load the community.<br/>Check the server connection and migration status.",empty_feed:"No posts yet.<br/>Leave the first anonymous question.",empty_hot:"No trending posts yet.",
    edit:"Edit",delete:"Delete",more_comments:"View all {count} comments",consult_tag:"consult-prep",comment_placeholder:"Write a comment · translation supported",comment_submit:"Post",
    translate_view:"Translate",translate_hide:"Hide translation",translating:"Translating...",translation_empty:"Translation result is empty.",translation_error:"Could not load translation.",
    input_required:"Please enter content first.",safety_checking:"AI is checking the wording...",suggested:"Suggested wording",safety_failed:"Could not complete the safety check. Please try again later.",
    title_content_required:"Please enter at least 2 characters for title and content.",post_created:"Posted to the community.",post_updated:"Post updated.",post_fail:"Could not post. Check privacy or legal-judgment wording.",
    comment_fail:"Could not post the comment. Please make the wording safer.",comments_fail:"Could not load comments.",delete_post_confirm:"Delete this post? It will no longer appear with comments or translations.",post_deleted:"Post deleted.",post_delete_fail:"Could not delete the post.",
    edit_comment_prompt:"Edit your comment.",comment_content_required:"Please enter comment content.",comment_updated:"Comment updated.",comment_update_fail:"Could not update the comment. Please make the wording safer.",delete_comment_confirm:"Delete this comment?",comment_deleted:"Comment deleted.",comment_delete_fail:"Could not delete the comment.",
    reaction_fail:"Could not save the reaction.",report_prompt:"Briefly enter the report reason.",report_done:"Report submitted.",report_fail:"Could not submit the report.",
    just_now:"Just now",min_ago:"{n}m ago",hour_ago:"{n}h ago",day_ago:"{n}d ago",
    cat_all:"Hot",cat_free:"Free",cat_wage:"Wage",cat_petition:"Complaint",cat_review:"Review",cat_mine:"Mine",cat_translation:"Translation",cat_notice:"Notice"
  },
  vi:{
    hero_label:"Cộng đồng",hero_title:"Hỏi điều bạn cần<br/>trước khi tư vấn",hero_body:"Hỏi ẩn danh về lương, hợp đồng, khoản khấu trừ, đơn khiếu nại và những nội dung cần chuẩn bị.",
    search_placeholder:"Tìm trường hợp tương tự",search_empty:"Không có bài viết phù hợp.<br/>Hãy thử từ khóa khác.",stat_posts:"Bài viết",stat_comments:"Bình luận",stat_saved:"Đã lưu",tab_all:"Nổi bật",tab_free:"Tự do",tab_wage:"Lương",tab_petition:"Đơn khiếu nại",tab_review:"Kinh nghiệm",tab_mine:"Bài của tôi",
    hot_title:"Bài được xem nhiều",refresh:"Làm mới",me:"Tôi",compose_entry:"Đặt câu hỏi ẩn danh",nav_community:"Cộng đồng",
    sheet_new:"Viết ẩn danh",sheet_edit:"Sửa bài viết",close:"Đóng",board_wage:"Lương/Khấu trừ",board_petition:"Đơn khiếu nại",board_review:"Kinh nghiệm tư vấn",board_free:"Tự do",
    title_placeholder:"Nhập tiêu đề",content_placeholder:"Viết nội dung muốn chuẩn bị trước tư vấn. Không đăng tên, số điện thoại hoặc số đăng ký người nước ngoài sẽ an toàn hơn.",
    safety_default:"Trước khi đăng, hãy kiểm tra thông tin cá nhân và cách viết quá khẳng định.",safety_edit:"Hãy kiểm tra nội dung sửa đã được viết an toàn chưa.",btn_safety:"Kiểm tra an toàn",btn_post:"Đăng",btn_update:"Cập nhật",
    loading:"Đang tải cộng đồng...",load_error:"Không thể tải cộng đồng.<br/>Hãy kiểm tra máy chủ và trạng thái migration.",empty_feed:"Chưa có bài viết.<br/>Hãy để lại câu hỏi ẩn danh đầu tiên.",empty_hot:"Chưa có bài nổi bật.",
    edit:"Sửa",delete:"Xóa",more_comments:"Xem tất cả {count} bình luận",consult_tag:"chuẩn-bị-tư-vấn",comment_placeholder:"Viết bình luận · hỗ trợ dịch",comment_submit:"Đăng",
    translate_view:"Dịch",translate_hide:"Ẩn bản dịch",translating:"Đang dịch...",translation_empty:"Kết quả dịch trống.",translation_error:"Không thể tải bản dịch.",
    input_required:"Vui lòng nhập nội dung trước.",safety_checking:"AI đang kiểm tra cách diễn đạt...",suggested:"Cách diễn đạt gợi ý",safety_failed:"Không thể hoàn tất kiểm tra. Vui lòng thử lại sau.",
    title_content_required:"Vui lòng nhập tiêu đề và nội dung ít nhất 2 ký tự.",post_created:"Đã đăng lên cộng đồng.",post_updated:"Đã sửa bài viết.",post_fail:"Không thể đăng. Hãy kiểm tra thông tin cá nhân hoặc cách diễn đạt pháp lý.",
    comment_fail:"Không thể đăng bình luận. Hãy viết an toàn hơn.",comments_fail:"Không thể tải bình luận.",delete_post_confirm:"Xóa bài viết này? Bài sẽ không còn hiển thị cùng bình luận và bản dịch.",post_deleted:"Đã xóa bài viết.",post_delete_fail:"Không thể xóa bài viết.",
    edit_comment_prompt:"Sửa nội dung bình luận.",comment_content_required:"Vui lòng nhập nội dung bình luận.",comment_updated:"Đã sửa bình luận.",comment_update_fail:"Không thể sửa bình luận. Hãy viết an toàn hơn.",delete_comment_confirm:"Xóa bình luận này?",comment_deleted:"Đã xóa bình luận.",comment_delete_fail:"Không thể xóa bình luận.",
    reaction_fail:"Không thể lưu phản ứng.",report_prompt:"Nhập ngắn gọn lý do báo cáo.",report_done:"Đã gửi báo cáo.",report_fail:"Không thể gửi báo cáo.",
    just_now:"Vừa xong",min_ago:"{n} phút trước",hour_ago:"{n} giờ trước",day_ago:"{n} ngày trước",
    cat_all:"Nổi bật",cat_free:"Tự do",cat_wage:"Lương",cat_petition:"Đơn",cat_review:"Kinh nghiệm",cat_mine:"Bài của tôi",cat_translation:"Dịch",cat_notice:"Thông báo"
  }
};

S.community=S.community||{category:"all",posts:[],loaded:false,loading:false,composingCategory:"wage",editingPostId:null,search:""};

function cmt(key,vars){
  const lang=COMMUNITY_TEXT[S.lang]?S.lang:(S.lang==="ko"?"ko":"en");
  let value=(COMMUNITY_TEXT[lang]&&COMMUNITY_TEXT[lang][key])||(COMMUNITY_TEXT.en&&COMMUNITY_TEXT.en[key])||(COMMUNITY_TEXT.ko&&COMMUNITY_TEXT.ko[key])||key;
  if(vars)Object.entries(vars).forEach(([k,v])=>{value=value.replaceAll("{"+k+"}",v);});
  return value;
}

function communityCategory(category){
  const lang=COMMUNITY_TEXT[S.lang]?S.lang:(S.lang==="ko"?"ko":"en");
  const key="cat_"+category;
  return (COMMUNITY_TEXT[lang]&&COMMUNITY_TEXT[lang][key])||
    (COMMUNITY_TEXT.en&&COMMUNITY_TEXT.en[key])||
    COMMUNITY_CATEGORIES[category]||
    category;
}

function applyCommunityLang(){
  document.querySelectorAll("[data-ck]").forEach(el=>{el.innerHTML=cmt(el.getAttribute("data-ck"));});
  document.querySelectorAll("[data-cph]").forEach(el=>{el.placeholder=cmt(el.getAttribute("data-cph"));});
  document.querySelectorAll("[data-caria]").forEach(el=>{el.setAttribute("aria-label",cmt(el.getAttribute("data-caria")));});
  const submit=document.getElementById("communitySubmitBtn");
  if(submit)submit.textContent=S.community&&S.community.editingPostId?cmt("btn_update"):cmt("btn_post");
  const title=document.getElementById("communitySheetTitle");
  if(title)title.innerHTML=S.community&&S.community.editingPostId?cmt("sheet_edit"):cmt("sheet_new");
  if(S.community&&S.community.loaded)renderCommunityFeed();
}

if(typeof window!=="undefined"&&typeof window.applyLang==="function"){
  const baseApplyLang=window.applyLang;
  window.applyLang=function(){
    baseApplyLang();
    applyCommunityLang();
  };
}

function goCommunity(){
  goPage("community",4);
  applyCommunityLang();
  if(!S.community.loaded)loadCommunityFeed();
}

async function loadCommunityFeed(){
  const feed=document.getElementById("communityFeed");
  if(!feed)return;
  S.community.loading=true;
  feed.innerHTML=`<div class="community-loading"><i class="ti ti-loader-2"></i><span>${esc(cmt("loading"))}</span></div>`;
  try{
    const mine=S.community.category==="mine";
    const cat=S.community.category&&S.community.category!=="all"&&!mine?"&category="+encodeURIComponent(S.community.category):"";
    const mineParam=mine?"&mine=true":"";
    const search=(S.community.search||"").trim();
    const searchParam=search?"&q="+encodeURIComponent(search):"";
    const sort=search?"latest":"hot";
    const res=await api("GET","/community/posts?sort="+sort+"&limit=30"+cat+mineParam+searchParam);
    S.community.posts=res.posts||[];
    S.community.loaded=true;
    updateCommunitySearchUi();
    renderCommunityFeed();
  }catch(e){
    feed.innerHTML=`<div class="community-empty"><i class="ti ti-wifi-off"></i>${cmt("load_error")}</div>`;
  }finally{
    S.community.loading=false;
  }
}

function renderCommunityFeed(){
  const posts=S.community.posts||[];
  renderCommunityStats(posts);
  renderCommunityHot(posts);
  const feed=document.getElementById("communityFeed");
  if(!feed)return;
  if(!posts.length){
    const searching=(S.community.search||"").trim().length>0;
    feed.innerHTML=`<div class="community-empty"><i class="ti ${searching?"ti-search-off":"ti-message-circle-plus"}"></i>${searching?cmt("search_empty"):cmt("empty_feed")}</div>`;
    return;
  }
  feed.innerHTML=posts.map(renderCommunityPost).join("");
}

function renderCommunityStats(posts){
  const postEl=document.getElementById("communityStatPosts");
  const commentEl=document.getElementById("communityStatComments");
  const savedEl=document.getElementById("communityStatSaved");
  if(postEl)postEl.textContent=formatCommunityCount(posts.length);
  if(commentEl)commentEl.textContent=formatCommunityCount(posts.reduce((s,p)=>s+(p.comment_count||0),0));
  if(savedEl)savedEl.textContent=formatCommunityCount(posts.reduce((s,p)=>s+(p.saved_count||0),0));
}

function renderCommunityHot(posts){
  const box=document.getElementById("communityHotList");
  if(!box)return;
  const panel=box.closest(".community-hot");
  if(panel)panel.style.display=(S.community.search||"").trim()?"none":"";
  const hot=[...posts].sort((a,b)=>communityScore(b)-communityScore(a)).slice(0,3);
  if(!hot.length){
    box.innerHTML=`<div class="community-empty" style="padding:14px">${esc(cmt("empty_hot"))}</div>`;
    return;
  }
  box.innerHTML=hot.map((p,i)=>`
    <button class="community-hot-row" type="button" onclick="focusCommunityPost('${esc(p.id)}')">
      <span class="community-hot-rank">${i+1}</span>
      <span class="community-hot-title">${esc(p.title)}</span>
      <span class="community-hot-meta"><i class="ti ti-heart"></i> ${formatCommunityCount(p.like_count||0)}</span>
    </button>
  `).join("");
}

function renderCommunityPost(post){
  const comments=(post.comments_preview||[]).map(renderCommunityComment).join("");
  const commentBox=comments?`<div class="community-comments">${comments}</div>`:"";
  const category=communityCategory(post.category)||COMMUNITY_CATEGORIES[post.category]||post.category;
  const lang=COMMUNITY_LANG[post.language_code]||post.language_code;
  const targetLang=S.lang||"ko";
  const translationId=`communityTranslation-${post.id}`;
  const riskBadge=post.risk_level==="safe"
    ?`<span class="community-badge"><i class="ti ti-shield-check"></i>safe</span>`
    :`<span class="community-badge warn"><i class="ti ti-alert-triangle"></i>${esc(post.risk_level)}</span>`;
  const ownerActions=post.my_owned?`
        <button class="community-action" type="button" onclick="openCommunityComposer('${esc(post.id)}')">
          <i class="ti ti-pencil"></i><span>${esc(cmt("edit"))}</span>
        </button>
        <button class="community-action owner-danger" type="button" onclick="deleteCommunityPost('${esc(post.id)}')">
          <i class="ti ti-trash"></i><span>${esc(cmt("delete"))}</span>
        </button>`:"";
  const moreComments=(post.comment_count||0)>(post.comments_preview||[]).length
    ?`<button class="community-load-comments" type="button" onclick="loadCommunityComments('${esc(post.id)}')">${esc(cmt("more_comments",{count:formatCommunityCount(post.comment_count)}))}</button>`
    :"";
  return `
    <article class="community-post" id="communityPost-${esc(post.id)}">
      <div class="community-post-head">
        <span class="community-avatar">${esc(initialOf(post.anonymous_name))}</span>
        <div class="community-post-author">
          <strong>${esc(post.anonymous_name)}</strong>
          <div class="community-post-meta">
            <span>${esc(category)}</span><span>·</span><span>${esc(lang)}</span><span>·</span><span>${formatCommunityTime(post.created_at)}</span>
          </div>
        </div>
        ${riskBadge}
      </div>
      <h3 class="community-post-title">${esc(post.title)}</h3>
      <div class="community-post-body">${esc(post.content)}</div>
      <div class="community-tags">
        <span>#${esc(category)}</span>
        <span>#${esc(lang)}</span>
        <span>#${esc(cmt("consult_tag"))}</span>
      </div>
      <div class="community-translation" id="${translationId}"></div>
      <div class="community-actions">
        <button class="community-action primary" type="button" onclick="toggleCommunityReaction('post','${esc(post.id)}','like')">
          <i class="ti ti-heart${post.my_liked?'-filled':''}"></i><span>${formatCommunityCount(post.like_count||0)}</span>
        </button>
        <button class="community-action" type="button" onclick="toggleCommunityReaction('post','${esc(post.id)}','save')">
          <i class="ti ti-bookmark${post.my_saved?'-filled':''}"></i><span>${formatCommunityCount(post.saved_count||0)}</span>
        </button>
        <button class="community-action" type="button" onclick="translateCommunity('post','${esc(post.id)}','${esc(targetLang)}',this)">
          <i class="ti ti-language"></i><span>${esc(cmt("translate_view"))}</span>
        </button>
        ${ownerActions}
        <button class="community-action danger" type="button" onclick="reportCommunity('post','${esc(post.id)}')">
          <i class="ti ti-flag"></i>
        </button>
      </div>
      ${commentBox}
      ${moreComments}
      <form class="community-comment-form" onsubmit="submitCommunityComment(event,'${esc(post.id)}')">
        <input id="communityComment-${esc(post.id)}" maxlength="2000" placeholder="${esc(cmt("comment_placeholder"))}" />
        <button type="submit">${esc(cmt("comment_submit"))}</button>
      </form>
    </article>
  `;
}

function renderCommunityComment(comment){
  const targetLang=S.lang||"ko";
  const translationId=`communityTranslation-${comment.id}`;
  const lang=COMMUNITY_LANG[comment.language_code]||comment.language_code;
  const ownerActions=comment.my_owned?`
        <button class="community-action" type="button" onclick="editCommunityComment('${esc(comment.id)}')">
          <i class="ti ti-pencil"></i><span>${esc(cmt("edit"))}</span>
        </button>
        <button class="community-action owner-danger" type="button" onclick="deleteCommunityComment('${esc(comment.id)}')">
          <i class="ti ti-trash"></i><span>${esc(cmt("delete"))}</span>
        </button>`:"";
  return `
    <div class="community-comment" id="communityCommentItem-${esc(comment.id)}">
      <div class="community-comment-meta">
        <span>${esc(comment.anonymous_name)}</span><span>·</span><span>${esc(lang)}</span><span>·</span><span>${formatCommunityTime(comment.created_at)}</span>
      </div>
      <div class="community-comment-body">${esc(comment.content)}</div>
      <div class="community-translation" id="${translationId}"></div>
      <div class="community-comment-actions">
        <button class="community-action" type="button" onclick="toggleCommunityReaction('comment','${esc(comment.id)}','like')">
          <i class="ti ti-heart${comment.my_liked?'-filled':''}"></i><span>${formatCommunityCount(comment.like_count||0)}</span>
        </button>
        <button class="community-action" type="button" onclick="translateCommunity('comment','${esc(comment.id)}','${esc(targetLang)}',this)">
          <i class="ti ti-language"></i><span>${esc(cmt("translate_view"))}</span>
        </button>
        ${ownerActions}
      </div>
    </div>
  `;
}

function selectCommunityCategory(category){
  S.community.category=category||"all";
  document.querySelectorAll("#communityTabs button").forEach(btn=>btn.classList.toggle("on",btn.dataset.category===S.community.category));
  loadCommunityFeed();
}

function handleCommunitySearch(value){
  S.community.search=String(value||"").trim();
  updateCommunitySearchUi();
  clearTimeout(window.__communitySearchTimer);
  window.__communitySearchTimer=setTimeout(()=>loadCommunityFeed(),260);
}

function clearCommunitySearch(){
  S.community.search="";
  const input=document.getElementById("communitySearchInput");
  if(input)input.value="";
  updateCommunitySearchUi();
  loadCommunityFeed();
}

function updateCommunitySearchUi(){
  const clear=document.getElementById("communitySearchClear");
  if(clear)clear.classList.toggle("show",Boolean((S.community.search||"").trim()));
}

function openCommunityComposer(postId){
  const sheet=document.getElementById("communitySheet");
  if(!sheet)return;
  const post=postId?findCommunityPost(postId):null;
  S.community.editingPostId=post?post.id:null;
  document.getElementById("communitySheetTitle").textContent=post?cmt("sheet_edit"):cmt("sheet_new");
  document.getElementById("communitySubmitBtn").textContent=post?cmt("btn_update"):cmt("btn_post");
  document.getElementById("communityTitleInput").value=post?post.title:"";
  document.getElementById("communityContentInput").value=post?post.content:"";
  S.community.composingCategory=post?post.category:(S.community.composingCategory||"wage");
  document.querySelectorAll("#communityBoardPicks button").forEach(btn=>{
    btn.classList.toggle("on",btn.dataset.category===S.community.composingCategory);
  });
  setCommunitySafetyBox("ok",post?cmt("safety_edit"):cmt("safety_default"));
  sheet.classList.add("show");
  sheet.setAttribute("aria-hidden","false");
  document.getElementById("communityTitleInput").focus();
}

function closeCommunityComposer(){
  const sheet=document.getElementById("communitySheet");
  if(!sheet)return;
  sheet.classList.remove("show");
  sheet.setAttribute("aria-hidden","true");
  S.community.editingPostId=null;
  document.getElementById("communitySheetTitle").textContent=cmt("sheet_new");
  document.getElementById("communitySubmitBtn").textContent=cmt("btn_post");
}

async function runCommunitySafetyCheck(){
  const title=document.getElementById("communityTitleInput").value.trim();
  const content=document.getElementById("communityContentInput").value.trim();
  const box=document.getElementById("communitySafeResult");
  if(!content&&!title){toast(cmt("input_required"));return;}
  setCommunitySafetyBox("checking",cmt("safety_checking"));
  try{
    const res=await api("POST","/community/safety-check",{content:[title,content].filter(Boolean).join("\n"),language:"auto"});
    const icon=res.allowed?"ti ti-shield-check":"ti ti-alert-triangle";
    box.classList.toggle("warn",res.moderation_status==="review");
    box.classList.toggle("block",!res.allowed);
    box.innerHTML=`<i class="${icon}"></i><span>${esc(res.message)}${res.suggested_text?`<br/><b>${esc(cmt("suggested"))}:</b> ${esc(res.suggested_text)}`:""}</span>`;
  }catch(e){
    setCommunitySafetyBox("warn",cmt("safety_failed"));
  }
}

async function submitCommunityPost(){
  const title=document.getElementById("communityTitleInput").value.trim();
  const content=document.getElementById("communityContentInput").value.trim();
  if(title.length<2||content.length<2){toast(cmt("title_content_required"));return;}
  try{
    const editingId=S.community.editingPostId;
    const payload={category:S.community.composingCategory||"free",title,content,language:"auto"};
    if(editingId){
      await api("PATCH",`/community/posts/${editingId}`,payload);
    }else{
      await api("POST","/community/posts",payload);
    }
    document.getElementById("communityTitleInput").value="";
    document.getElementById("communityContentInput").value="";
    setCommunitySafetyBox("ok",editingId?cmt("post_updated"):cmt("post_created"));
    closeCommunityComposer();
    if(!editingId){
      S.community.category="all";
      document.querySelectorAll("#communityTabs button").forEach(btn=>btn.classList.toggle("on",btn.dataset.category==="all"));
    }
    await loadCommunityFeed();
    toast(editingId?cmt("post_updated"):cmt("post_created"));
  }catch(e){
    let msg=cmt("post_fail");
    try{
      const detail=JSON.parse(e.message).detail;
      if(detail&&detail.message)msg=detail.message;
    }catch(_){}
    setCommunitySafetyBox("block",msg);
  }
}

async function submitCommunityComment(event,postId){
  event.preventDefault();
  const input=document.getElementById(`communityComment-${postId}`);
  const content=input.value.trim();
  if(!content)return;
  input.disabled=true;
  try{
    await api("POST",`/community/posts/${postId}/comments`,{content,language:"auto"});
    input.value="";
    await loadCommunityFeed();
  }catch(e){
    toast(cmt("comment_fail"));
  }finally{
    input.disabled=false;
  }
}

async function loadCommunityComments(postId){
  try{
    const res=await api("GET",`/community/posts/${postId}/comments?limit=100`);
    const post=findCommunityPost(postId);
    if(post){
      post.comments_preview=res.comments||[];
      post.comment_count=Math.max(post.comment_count||0,post.comments_preview.length);
      renderCommunityFeed();
      focusCommunityPost(postId);
    }
  }catch(e){
    toast(cmt("comments_fail"));
  }
}

async function deleteCommunityPost(postId){
  if(!confirm(cmt("delete_post_confirm")))return;
  try{
    await api("DELETE",`/community/posts/${postId}`);
    S.community.posts=(S.community.posts||[]).filter(p=>p.id!==postId);
    renderCommunityFeed();
    toast(cmt("post_deleted"));
  }catch(e){
    toast(cmt("post_delete_fail"));
  }
}

async function editCommunityComment(commentId){
  const comment=findCommunityComment(commentId);
  if(!comment)return;
  const content=prompt(cmt("edit_comment_prompt"),comment.content);
  if(content===null)return;
  const trimmed=content.trim();
  if(!trimmed){toast(cmt("comment_content_required"));return;}
  try{
    await api("PATCH",`/community/comments/${commentId}`,{content:trimmed,language:"auto"});
    await loadCommunityFeed();
    toast(cmt("comment_updated"));
  }catch(e){
    toast(cmt("comment_update_fail"));
  }
}

async function deleteCommunityComment(commentId){
  if(!confirm(cmt("delete_comment_confirm")))return;
  try{
    await api("DELETE",`/community/comments/${commentId}`);
    await loadCommunityFeed();
    toast(cmt("comment_deleted"));
  }catch(e){
    toast(cmt("comment_delete_fail"));
  }
}

async function toggleCommunityReaction(targetType,targetId,reactionType){
  try{
    await api("POST","/community/reactions",{target_type:targetType,target_id:targetId,reaction_type:reactionType});
    await loadCommunityFeed();
  }catch(e){
    toast(cmt("reaction_fail"));
  }
}

async function translateCommunity(targetType,targetId,targetLanguage,button){
  const box=document.getElementById(`communityTranslation-${targetId}`);
  if(!box)return;
  if(box.classList.contains("show")){
    box.classList.remove("show");
    if(button)button.querySelector("span").textContent=cmt("translate_view");
    return;
  }
  box.classList.add("show");
  box.innerHTML=`<span class="community-loading" style="padding:0"><i class="ti ti-loader-2"></i>${esc(cmt("translating"))}</span>`;
  try{
    const res=await api("POST","/community/translate",{target_type:targetType,target_id:targetId,target_language:targetLanguage||"ko"});
    box.textContent=res.translated_text||cmt("translation_empty");
    if(button)button.querySelector("span").textContent=cmt("translate_hide");
  }catch(e){
    box.textContent=cmt("translation_error");
  }
}

async function reportCommunity(targetType,targetId){
  const reason=prompt(cmt("report_prompt"));
  if(!reason||reason.trim().length<2)return;
  try{
    await api("POST","/community/reports",{target_type:targetType,target_id:targetId,reason:reason.trim()});
    toast(cmt("report_done"));
  }catch(e){
    toast(cmt("report_fail"));
  }
}

function focusCommunityPost(postId){
  const el=document.getElementById(`communityPost-${postId}`);
  if(!el)return;
  el.scrollIntoView({behavior:"smooth",block:"start"});
  el.animate([{boxShadow:"0 0 0 0 rgba(37,99,235,.35)"},{boxShadow:"0 0 0 6px rgba(37,99,235,.12)"},{boxShadow:"0 10px 26px rgba(15,23,42,.05)"}],{duration:900,easing:"ease-out"});
}

function setCommunitySafetyBox(state,message){
  const box=document.getElementById("communitySafeResult");
  if(!box)return;
  box.classList.toggle("warn",state==="warn"||state==="checking");
  box.classList.toggle("block",state==="block");
  const icon=state==="checking"?"ti ti-loader-2":state==="block"?"ti ti-alert-triangle":"ti ti-shield-check";
  box.innerHTML=`<i class="${icon}"></i><span>${esc(message)}</span>`;
}

function formatCommunityCount(n){
  n=Number(n||0);
  if(S.lang==="ko"){
    if(n>=10000)return Math.floor(n/1000)/10+"만";
    if(n>=1000)return Math.floor(n/100)/10+"천";
    return String(n);
  }
  if(n>=1000000)return Math.floor(n/100000)/10+"M";
  if(n>=1000)return Math.floor(n/100)/10+"K";
  return String(n);
}

function formatCommunityTime(value){
  if(!value)return cmt("just_now");
  const then=new Date(value).getTime();
  if(Number.isNaN(then))return cmt("just_now");
  const diff=Math.max(0,Date.now()-then);
  const min=Math.floor(diff/60000);
  if(min<1)return cmt("just_now");
  if(min<60)return cmt("min_ago",{n:min});
  const hour=Math.floor(min/60);
  if(hour<24)return cmt("hour_ago",{n:hour});
  const day=Math.floor(hour/24);
  if(day<7)return cmt("day_ago",{n:day});
  return new Date(value).toLocaleDateString(S.lang==="ko"?"ko-KR":S.lang);
}

function communityScore(post){
  return (post.like_count||0)*3+(post.comment_count||0)*5+(post.saved_count||0)*4+(post.view_count||0)*0.1;
}

function initialOf(name){
  const s=String(name||"?").trim();
  return s.length>1?s.slice(-2):s;
}

function findCommunityPost(postId){
  return (S.community.posts||[]).find(p=>p.id===postId)||null;
}

function findCommunityComment(commentId){
  for(const post of (S.community.posts||[])){
    const comment=(post.comments_preview||[]).find(c=>c.id===commentId);
    if(comment)return comment;
  }
  return null;
}

(function initCommunity(){
  const tabs=document.getElementById("communityTabs");
  if(tabs){
    tabs.querySelectorAll("button").forEach(btn=>{
      btn.addEventListener("click",()=>selectCommunityCategory(btn.dataset.category));
    });
  }
  const picks=document.getElementById("communityBoardPicks");
  if(picks){
    picks.querySelectorAll("button").forEach(btn=>{
      btn.addEventListener("click",()=>{
        S.community.composingCategory=btn.dataset.category||"free";
        picks.querySelectorAll("button").forEach(b=>b.classList.toggle("on",b===btn));
      });
    });
  }
  const sheet=document.getElementById("communitySheet");
  if(sheet){
    sheet.addEventListener("click",event=>{
      if(event.target===sheet)closeCommunityComposer();
    });
  }
  const search=document.getElementById("communitySearchInput");
  if(search){
    search.addEventListener("input",event=>handleCommunitySearch(event.target.value));
    search.addEventListener("search",event=>handleCommunitySearch(event.target.value));
  }
  updateCommunitySearchUi();
})();
