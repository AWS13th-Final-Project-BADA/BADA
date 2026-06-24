import type {
  AnalysisReport,
  Case,
  CaseCreate,
  ChatResponse,
  CommunityComment,
  CommunityPost,
  EvidenceItem,
  PresignResult,
} from "./types";

export const DEMO_TOKEN = "__bada_demo_session__";

const now = () => new Date().toISOString();

let cases: Case[] = [
  {
    id: "demo-case-1",
    workplace_name: "바다식품",
    employer_name: "김대표",
    work_start_date: "2026-05-01",
    work_end_date: null,
    agreed_hourly_wage: 10030,
    agreed_weekly_hours: 40,
    issue_types: ["wage_unpaid", "deduction"],
    status: "collecting",
  },
];

let evidences: Record<string, EvidenceItem[]> = {
  "demo-case-1": [
    {
      id: "demo-ev-1",
      file_name: "급여명세서_5월.pdf",
      category: "statement",
      ocr_status: "completed",
    },
    {
      id: "demo-ev-2",
      file_name: "입금내역_5월.png",
      category: "payment",
      ocr_status: "completed",
    },
    {
      id: "demo-ev-3",
      file_name: "근로계약서.pdf",
      category: "contract",
      ocr_status: "completed",
    },
  ],
};

let posts: CommunityPost[] = [
  {
    id: "demo-post-1",
    category: "wage",
    title: "급여명세서와 입금액이 달라요",
    content:
      "급여명세서에는 230만원으로 적혀 있는데 실제 입금은 190만원만 됐어요. 상담 전에 어떤 자료를 준비하면 좋을까요?",
    language_code: "ko",
    anonymous_name: "익명 근로자 147",
    status: "active",
    like_count: 24,
    comment_count: 2,
    view_count: 128,
    created_at: now(),
    my_liked: false,
    my_owned: false,
    comments_preview: [],
  },
  {
    id: "demo-post-2",
    category: "petition",
    title: "진정서 쓰기 전에 확인할 게 있을까요?",
    content:
      "계약서, 입금내역, 카카오톡 대화는 모아뒀는데 근무시간 기록이 부족합니다. 먼저 상담을 가도 될지 궁금해요.",
    language_code: "ko",
    anonymous_name: "익명 82",
    status: "active",
    like_count: 18,
    comment_count: 5,
    view_count: 94,
    created_at: now(),
    my_liked: true,
    my_owned: false,
    comments_preview: [],
  },
];

let comments: Record<string, CommunityComment[]> = {
  "demo-post-1": [
    {
      id: "demo-comment-1",
      post_id: "demo-post-1",
      parent_comment_id: null,
      anonymous_name: "익명 82",
      content: "상담 갈 때 근로계약서랑 입금내역을 같은 달끼리 나란히 보여줬어요.",
      language_code: "ko",
      like_count: 12,
      created_at: now(),
    },
    {
      id: "demo-comment-2",
      post_id: "demo-post-1",
      parent_comment_id: null,
      anonymous_name: "익명 31",
      content: "공제 항목 설명을 들은 적이 있는지도 메모해두면 좋습니다.",
      language_code: "ko",
      like_count: 8,
      created_at: now(),
    },
  ],
  "demo-post-2": [
    {
      id: "demo-comment-3",
      post_id: "demo-post-2",
      parent_comment_id: null,
      anonymous_name: "상담 경험자",
      content: "부족한 자료는 상담기관에서 추가로 알려줘서, 현재 가진 자료부터 정리해 가도 도움이 됐어요.",
      language_code: "ko",
      like_count: 5,
      created_at: now(),
    },
  ],
};

function pathOnly(path: string) {
  return path.split("?")[0];
}

function readBody<T>(options: RequestInit = {}): T {
  if (!options.body || typeof options.body !== "string") return {} as T;
  return JSON.parse(options.body) as T;
}

export function isDemoToken(token: string | null): boolean {
  return token === DEMO_TOKEN;
}

export async function handleDemoApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const cleanPath = pathOnly(path);

  if (cleanPath === "/auth/me") {
    return {
      id: "demo-user",
      email: "demo@bada.local",
      name: "김바다",
      preferred_lang: "ko",
      provider: "demo",
    } as T;
  }

  if (cleanPath === "/cases" && method === "GET") {
    return cases as T;
  }

  if (cleanPath === "/cases" && method === "POST") {
    const body = readBody<CaseCreate>(options);
    const created: Case = {
      id: `demo-case-${Date.now()}`,
      workplace_name: body.workplace_name || "새 사업장",
      employer_name: body.employer_name || null,
      work_start_date: body.work_start_date || null,
      work_end_date: body.work_end_date || null,
      agreed_hourly_wage: body.agreed_hourly_wage || null,
      agreed_weekly_hours: body.agreed_weekly_hours || null,
      issue_types: body.issue_types || ["wage_unpaid"],
      status: "collecting",
    };
    cases = [created, ...cases];
    evidences[created.id] = [];
    return created as T;
  }

  const caseMatch = cleanPath.match(/^\/cases\/([^/]+)$/);
  if (caseMatch && method === "GET") {
    const found = cases.find((item) => item.id === caseMatch[1]) || cases[0];
    return found as T;
  }

  const evidenceMatch = cleanPath.match(/^\/cases\/([^/]+)\/evidences$/);
  if (evidenceMatch && method === "GET") {
    return (evidences[evidenceMatch[1]] || []) as T;
  }

  if (evidenceMatch && method === "POST") {
    const caseId = evidenceMatch[1];
    const body = readBody<{ file_name?: string; category?: string }>(options);
    const item: EvidenceItem = {
      id: `demo-ev-${Date.now()}`,
      file_name: body.file_name || "증거자료",
      category: body.category || "other",
      ocr_status: "completed",
    };
    evidences[caseId] = [item, ...(evidences[caseId] || [])];
    return {
      evidence_id: item.id,
      upload_url: null,
      file_key: `demo/${item.id}`,
    } satisfies PresignResult as T;
  }

  if (/^\/cases\/[^/]+\/analysis$/.test(cleanPath) || /^\/cases\/[^/]+\/analyze$/.test(cleanPath)) {
    return demoReport(cleanPath.split("/")[2]) as T;
  }

  if (cleanPath === "/community/posts" && method === "GET") {
    return { posts } as T;
  }

  if (cleanPath === "/community/posts" && method === "POST") {
    const body = readBody<{ category?: string; title?: string; content?: string; language?: string }>(options);
    const post: CommunityPost = {
      id: `demo-post-${Date.now()}`,
      category: body.category || "free",
      title: body.title || "새 글",
      content: body.content || "",
      language_code: body.language || "ko",
      anonymous_name: "익명",
      status: "active",
      like_count: 0,
      comment_count: 0,
      view_count: 1,
      created_at: now(),
      my_liked: false,
      my_owned: true,
      comments_preview: [],
    };
    posts = [post, ...posts];
    comments[post.id] = [];
    return post as T;
  }

  const postMatch = cleanPath.match(/^\/community\/posts\/([^/]+)$/);
  if (postMatch && method === "GET") {
    const post = posts.find((item) => item.id === postMatch[1]) || posts[0];
    return post as T;
  }

  const commentsMatch = cleanPath.match(/^\/community\/posts\/([^/]+)\/comments$/);
  if (commentsMatch && method === "GET") {
    return { comments: comments[commentsMatch[1]] || [] } as T;
  }

  if (commentsMatch && method === "POST") {
    const body = readBody<{ content?: string; language?: string }>(options);
    const postId = commentsMatch[1];
    const comment: CommunityComment = {
      id: `demo-comment-${Date.now()}`,
      post_id: postId,
      parent_comment_id: null,
      anonymous_name: "익명",
      content: body.content || "",
      language_code: body.language || "ko",
      like_count: 0,
      created_at: now(),
    };
    comments[postId] = [...(comments[postId] || []), comment];
    posts = posts.map((post) =>
      post.id === postId ? { ...post, comment_count: (post.comment_count || 0) + 1 } : post
    );
    return comment as T;
  }

  if (cleanPath === "/community/reactions" && method === "POST") {
    return { like_count: 13, active: true } as T;
  }

  if (cleanPath === "/chat/messages" && method === "POST") {
    const body = readBody<{ message?: string }>(options);
    return {
      answer:
        body.message?.includes("진정서")
          ? "진정서에는 본인 정보, 사업장 정보, 근무 기간, 약속한 임금과 실제 입금액, 보유 증빙자료 목록을 시간 순서대로 정리하면 좋습니다. BADA는 법률 판단을 하지 않으며, 최종 판단은 상담기관에서 확인해야 합니다."
          : "현재 자료 기준으로 급여명세서와 입금내역 사이의 차이를 상담 전 쟁점으로 정리할 수 있습니다. 계약서, 입금내역, 급여명세서를 같은 기간끼리 묶어 준비해 보세요.",
      intent: "preparation_guidance",
      risk_level: "safe",
      ai_provider: "demo",
      used_case_context: true,
      used_rag: true,
      fallback_used: false,
      next_actions: ["급여명세서와 입금내역 비교", "근로계약서 추가", "상담 질문 목록 작성"],
      disclaimer: "이 답변은 법률 판단이 아니라 상담 전 준비 안내입니다.",
      sources: [{ title: "고용노동부 상담 준비 안내" }],
    } satisfies ChatResponse as T;
  }

  if (/^\/cases\/[^/]+\/gps\/workplace$/.test(cleanPath)) {
    return { center_lat: 37.5665, center_lng: 126.978, radius_m: 80 } as T;
  }

  if (/^\/cases\/[^/]+\/gps\/ping$/.test(cleanPath)) {
    return { ok: true, inside: true, status: "IN_WORKPLACE", distance_m: 12 } as T;
  }

  return null as T;
}

function demoReport(caseId: string): AnalysisReport {
  return {
    schema_version: "demo",
    case: {
      id: caseId,
      workplace: "바다식품",
      employer: "김대표",
      issue_types: ["wage_unpaid", "deduction"],
    },
    wage: {
      currency: "KRW",
      computable: true,
      agreed_hourly: 10030,
      expected: 2300000,
      received: 1900000,
      suspected_unpaid: 400000,
      basis: "급여명세서 2,300,000원과 입금내역 1,900,000원을 비교했습니다.",
      notes: ["공제 항목은 상담기관에서 추가 확인이 필요합니다."],
    },
    deductions: [
      { name: "기숙사비", category: "housing", amount: 200000, currency: "KRW", sources: ["급여명세서"], verify: "동의 자료 확인 필요" },
      { name: "식비", category: "meal", amount: 100000, currency: "KRW", sources: ["급여명세서"], verify: "공제 설명 확인 필요" },
    ],
    legal: {
      min_wage: { year: 2026, hourly: 10030 },
      findings: [
        {
          type: "wage_difference",
          severity: "medium",
          message: "임금 차액으로 보이는 금액이 있어 상담 전 자료 정리가 필요합니다.",
          amount: 400000,
        },
      ],
    },
    timeline: [
      {
        date: "2026-05-31",
        type: "payment",
        text: "5월 급여 입금 1,900,000원 확인",
        text_translated: null,
        source_evidence_id: "demo-ev-2",
        confidence: "high",
      },
      {
        date: "2026-06-01",
        type: "document",
        text: "급여명세서상 지급액 2,300,000원 확인",
        text_translated: null,
        source_evidence_id: "demo-ev-1",
        confidence: "high",
      },
    ],
    missing: [
      { item: "근무시간 기록", reason: "약속 임금과 실제 근무시간 비교에 필요합니다." },
      { item: "공제 동의 또는 설명 자료", reason: "공제 항목 확인에 필요합니다." },
    ],
    narrative: {
      summary: "현재 자료 기준으로 400,000원 차이가 확인되며 상담 전 자료 정리가 필요합니다.",
      disclaimer: "BADA는 법률 판단을 하지 않으며 최종 판단은 상담기관에서 확인해야 합니다.",
    },
    meta: { generated_at: now(), lang: "ko", provider_mode: "demo" },
  };
}
