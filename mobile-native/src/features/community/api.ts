import { fetchApi } from "@/lib/api";
import type {
  CommunityCategory,
  CommunityComment,
  CommunityDeleteResult,
  CommunityPost,
  CommunityReactionResult,
  CommunitySafetyResult,
  CommunityTranslationResult,
} from "./types";

export type CommunityTargetType = "post" | "comment";
export type CommunityReactionType = "like" | "save";

export function listCommunityPosts(options: {
  category?: string;
  sort?: "hot" | "latest";
  query?: string;
  mine?: boolean;
  limit?: number;
} = {}): Promise<{ posts: CommunityPost[] }> {
  const params = new URLSearchParams();
  if (options.category && options.category !== "all") params.set("category", options.category);
  if (options.sort) params.set("sort", options.sort);
  if (options.query?.trim()) params.set("q", options.query.trim());
  if (options.mine) params.set("mine", "true");
  params.set("limit", String(options.limit ?? 30));
  return fetchApi(`/community/posts?${params.toString()}`);
}

export function getCommunityPost(postId: string): Promise<CommunityPost> {
  return fetchApi(`/community/posts/${postId}`);
}

export function createCommunityPost(payload: {
  category: CommunityCategory;
  title: string;
  content: string;
  language: string;
}): Promise<CommunityPost> {
  return fetchApi("/community/posts", { method: "POST", body: JSON.stringify(payload) });
}

export function updateCommunityPost(
  postId: string,
  payload: { category: CommunityCategory; title: string; content: string; language: string }
): Promise<CommunityPost> {
  return fetchApi(`/community/posts/${postId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteCommunityPost(postId: string): Promise<CommunityDeleteResult> {
  return fetchApi(`/community/posts/${postId}`, { method: "DELETE" });
}

export function listCommunityComments(postId: string): Promise<{ comments: CommunityComment[] }> {
  return fetchApi(`/community/posts/${postId}/comments?limit=100`);
}

export function createCommunityComment(
  postId: string,
  payload: { content: string; language: string; parent_comment_id?: string | null }
): Promise<CommunityComment> {
  return fetchApi(`/community/posts/${postId}/comments`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCommunityComment(
  commentId: string,
  payload: { content: string; language: string }
): Promise<CommunityComment> {
  return fetchApi(`/community/comments/${commentId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteCommunityComment(commentId: string): Promise<CommunityDeleteResult> {
  return fetchApi(`/community/comments/${commentId}`, { method: "DELETE" });
}

export function toggleCommunityReaction(
  targetType: CommunityTargetType,
  targetId: string,
  reactionType: CommunityReactionType
): Promise<CommunityReactionResult> {
  return fetchApi("/community/reactions", {
    method: "POST",
    body: JSON.stringify({ target_type: targetType, target_id: targetId, reaction_type: reactionType }),
  });
}

export function translateCommunityTarget(
  targetType: CommunityTargetType,
  targetId: string,
  targetLanguage: string
): Promise<CommunityTranslationResult> {
  return fetchApi("/community/translate", {
    method: "POST",
    body: JSON.stringify({ target_type: targetType, target_id: targetId, target_language: targetLanguage }),
  });
}

export function reportCommunityTarget(
  targetType: CommunityTargetType,
  targetId: string,
  reason: string,
  description?: string
): Promise<{ id: string; status: string }> {
  return fetchApi("/community/reports", {
    method: "POST",
    body: JSON.stringify({ target_type: targetType, target_id: targetId, reason, description }),
  });
}

export function checkCommunitySafety(content: string, language: string): Promise<CommunitySafetyResult> {
  return fetchApi("/community/safety-check", {
    method: "POST",
    body: JSON.stringify({ content, language }),
  });
}