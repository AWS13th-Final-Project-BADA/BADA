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
  petition: "진정서",
  review: "후기",
  translation: "번역",
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
  moderation_status: string;
  risk_level: string;
  like_count: number;
  comment_count: number;
  saved_count: number;
  view_count: number;
  created_at: string;
  my_liked: boolean;
  my_saved: boolean;
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
  status: string;
  moderation_status: string;
  risk_level: string;
  like_count: number;
  reply_count: number;
  created_at: string;
  my_liked: boolean;
  my_owned: boolean;
}

export interface CommunitySafetyResult {
  allowed: boolean;
  risk_level: string;
  moderation_status: string;
  language: string;
  message: string;
  suggested_text: string | null;
}

export interface CommunityReactionResult {
  active: boolean;
  like_count: number | null;
  saved_count: number | null;
}

export interface CommunityTranslationResult {
  target_type: "post" | "comment";
  target_id: string;
  source_language: string;
  target_language: string;
  translated_text: string;
  provider: string;
  cached: boolean;
}

export interface CommunityDeleteResult {
  id: string;
  status: string;
  deleted: boolean;
}
