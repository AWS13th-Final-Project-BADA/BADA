export type Category =
  | "contract"
  | "schedule"
  | "payment"
  | "chat"
  | "statement"
  | "other";

export type FileType = "image" | "pdf" | "text";
export type Confidence = "high" | "medium" | "low";

export interface Case {
  id: string;
  workplace_name: string | null;
  employer_name: string | null;
  work_start_date: string | null;
  work_end_date: string | null;
  agreed_hourly_wage: number | null;
  agreed_weekly_hours: number | null;
  issue_types: string[];
  status: string;
}

export interface CaseCreate {
  workplace_name?: string | null;
  employer_name?: string | null;
  work_start_date?: string | null;
  work_end_date?: string | null;
  agreed_hourly_wage?: number | null;
  agreed_weekly_hours?: number | null;
  issue_types?: string[];
}

export interface PresignResult {
  evidence_id: string;
  upload_url: string | null;
  file_key: string;
}

export interface EvidenceItem {
  id: string;
  file_name: string;
  category: string;
  ocr_status: string | null;
}

export interface Wage {
  currency: string;
  computable: boolean;
  agreed_hourly: number | null;
  expected: number | null;
  received: number | null;
  suspected_unpaid: number | null;
  basis: string | null;
  notes: string[];
}

export interface Deduction {
  name: string;
  category: string;
  amount: number;
  currency: string;
  sources: string[];
  verify: string;
}

export interface Finding {
  type: string;
  severity: Confidence;
  message: string;
  amount: number | null;
}

export interface Legal {
  min_wage: { year: number; hourly: number };
  findings: Finding[];
}

export interface TimelineItem {
  date: string | null;
  type: string;
  text: string;
  text_translated: string | null;
  source_evidence_id: string | null;
  confidence: Confidence;
}

export interface MissingItem {
  item: string;
  reason: string;
}

export interface Narrative {
  summary: string;
  disclaimer: string;
}

export interface AnalysisReport {
  schema_version: string;
  case: {
    id: string;
    workplace: string | null;
    employer: string | null;
    issue_types: string[];
  };
  wage: Wage;
  deductions: Deduction[];
  legal: Legal;
  timeline: TimelineItem[];
  missing: MissingItem[];
  narrative: Narrative;
  meta: { generated_at: string | null; lang: string; provider_mode: string };
}

export const ISSUE_TYPES = [
  "wage_unpaid",
  "deduction",
  "overtime",
  "severance",
  "other",
] as const;

export const ISSUE_LABELS: Record<string, string> = {
  wage_unpaid: "임금 미지급",
  deduction: "공제 확인",
  overtime: "연장·야간수당",
  severance: "퇴직금",
  other: "기타",
};

export const CATEGORY_FILETYPE: Record<Category, FileType> = {
  contract: "pdf",
  schedule: "image",
  payment: "image",
  chat: "image",
  statement: "pdf",
  other: "image",
};

export type CommunityCategory =
  | "free"
  | "wage"
  | "petition"
  | "review"
  | "translation"
  | "notice";

export const COMMUNITY_CATEGORY_LABELS: Record<string, string> = {
  free: "자유",
  wage: "임금",
  petition: "진정/신고",
  review: "후기",
  translation: "번역요청",
  notice: "공지",
};

export interface CommunityPost {
  id: string;
  category: string;
  title: string;
  content: string;
  language_code: string;
  anonymous_name: string;
  status: string;
  like_count: number;
  comment_count: number;
  view_count: number;
  created_at: string;
  my_liked: boolean;
  my_owned: boolean;
  comments_preview: CommunityComment[];
}

export interface CommunityComment {
  id: string;
  post_id: string;
  parent_comment_id: string | null;
  anonymous_name: string;
  content: string;
  language_code: string;
  like_count: number;
  created_at: string;
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
  sources: { title?: string; url?: string }[];
}
