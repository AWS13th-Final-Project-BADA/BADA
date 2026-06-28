/** AI 챗봇(chat) 타입 — backend schemas_ai_chat.py. */

export interface ChatSource {
  source_id: string;
  title: string;
  source_org: string;
  section?: string | null;
  excerpt?: string | null;
  retrieval_method?: "keyword" | "vector" | "hybrid" | string | null;
}

export interface ChatResponse {
  answer: string;
  intent: string;
  risk_level: string;
  ai_provider: string;
  used_case_context: boolean;
  used_rag: boolean;
  fallback_used: boolean;
  next_actions: string[];
  disclaimer: string;
  sources: ChatSource[];
}
