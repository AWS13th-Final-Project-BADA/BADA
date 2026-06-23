import { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useLocalSearchParams, useFocusEffect } from "expo-router";
import { fetchApi } from "@/lib/api";
import type { CommunityPost, CommunityComment } from "@/lib/types";
import { COMMUNITY_CATEGORY_LABELS } from "@/lib/types";
import { colors, spacing, radius } from "@/theme";

export default function PostDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [post, setPost] = useState<CommunityPost | null>(null);
  const [comments, setComments] = useState<CommunityComment[]>([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([
        fetchApi<CommunityPost>(`/community/posts/${id}`),
        fetchApi<{ comments: CommunityComment[] }>(
          `/community/posts/${id}/comments`
        ).catch(() => ({ comments: [] })),
      ]);
      setPost(p);
      setComments(c.comments ?? []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  async function like() {
    if (!post) return;
    try {
      const r = await fetchApi<{ like_count: number; active: boolean }>(
        `/community/reactions`,
        {
          method: "POST",
          body: JSON.stringify({
            target_type: "post",
            target_id: post.id,
            reaction_type: "like",
          }),
        }
      );
      setPost({ ...post, like_count: r.like_count ?? post.like_count, my_liked: r.active });
    } catch (e: any) {
      Alert.alert("오류", String(e?.message ?? e));
    }
  }

  async function addComment() {
    if (text.trim().length < 1) return;
    setSending(true);
    try {
      await fetchApi(`/community/posts/${id}/comments`, {
        method: "POST",
        body: JSON.stringify({ content: text.trim(), language: "auto" }),
      });
      setText("");
      await load();
    } catch (e: any) {
      Alert.alert("등록 실패", String(e?.message ?? e));
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }
  if (!post) {
    return (
      <View style={styles.center}>
        <Text style={{ color: colors.textMuted }}>글을 찾을 수 없습니다.</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.cat}>
        {COMMUNITY_CATEGORY_LABELS[post.category] ?? post.category}
      </Text>
      <Text style={styles.title}>{post.title}</Text>
      <Text style={styles.meta}>
        {post.anonymous_name} · {post.created_at?.slice(0, 10)} · 조회 {post.view_count}
      </Text>
      <Text style={styles.body}>{post.content}</Text>

      <Pressable style={[styles.like, post.my_liked && styles.likeOn]} onPress={like}>
        <Text style={[styles.likeText, post.my_liked && { color: "#fff" }]}>
          ♡ 공감 {post.like_count}
        </Text>
      </Pressable>

      <Text style={styles.commentsTitle}>댓글 {comments.length}</Text>
      {comments.map((c) => (
        <View key={c.id} style={styles.comment}>
          <Text style={styles.commentMeta}>
            {c.anonymous_name} · {c.created_at?.slice(0, 10)}
          </Text>
          <Text style={styles.commentBody}>{c.content}</Text>
        </View>
      ))}
      {comments.length === 0 && (
        <Text style={styles.muted}>첫 댓글을 남겨보세요.</Text>
      )}

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={text}
          onChangeText={setText}
          placeholder="댓글 입력 (익명)"
          multiline
        />
        <Pressable style={styles.send} onPress={addComment} disabled={sending}>
          {sending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.sendText}>등록</Text>
          )}
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.sm },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  cat: { fontSize: 12, color: colors.primary, fontWeight: "700" },
  title: { fontSize: 20, fontWeight: "800", color: colors.text },
  meta: { fontSize: 12, color: colors.textMuted },
  body: { fontSize: 15, color: colors.text, lineHeight: 22, marginVertical: spacing.sm },
  like: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  likeOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  likeText: { color: colors.text, fontWeight: "600", fontSize: 13 },
  commentsTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: colors.text,
    marginTop: spacing.md,
  },
  comment: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: spacing.sm,
    gap: 2,
  },
  commentMeta: { fontSize: 11, color: colors.textMuted },
  commentBody: { fontSize: 14, color: colors.text },
  muted: { color: colors.textMuted, fontSize: 13 },
  inputRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md, alignItems: "flex-end" },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: spacing.sm,
    backgroundColor: "#fff",
    maxHeight: 100,
  },
  send: {
    backgroundColor: colors.primary,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    justifyContent: "center",
  },
  sendText: { color: "#fff", fontWeight: "700" },
});
