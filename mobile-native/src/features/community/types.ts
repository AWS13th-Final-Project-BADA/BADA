/** 커뮤니티(community) 타입 — backend schemas_community.py. */

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
