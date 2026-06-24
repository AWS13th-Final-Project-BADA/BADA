import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { fetchApi } from "@/lib/api";
import type { CommunityComment, CommunityPost } from "@/lib/types";
import { COMMUNITY_CATEGORY_LABELS } from "@/lib/types";
import { Card, RemoteImage, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { stitchImages } from "@/lib/stitchAssets";

export default function CommunityPostDetail() {
  const { id = "demo-post-1" } = useLocalSearchParams<{ id?: string }>();
  const [post, setPost] = useState<CommunityPost | null>(null);
  const [comments, setComments] = useState<CommunityComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      try {
        const [nextPost, nextComments] = await Promise.all([
          fetchApi<CommunityPost>(`/community/posts/${id}`),
          fetchApi<{ comments: CommunityComment[] }>(`/community/posts/${id}/comments`),
        ]);
        if (!alive) return;
        setPost(nextPost);
        setComments(nextComments.comments ?? nextPost.comments_preview ?? []);
      } finally {
        if (alive) setLoading(false);
      }
    }
    void load();
    return () => {
      alive = false;
    };
  }, [id]);

  async function sendComment() {
    const text = comment.trim();
    if (!text || sending) return;
    setSending(true);
    try {
      const created = await fetchApi<CommunityComment>(`/community/posts/${id}/comments`, {
        method: "POST",
        body: JSON.stringify({ content: text, language: "ko" }),
      });
      setComments((prev) => [...prev, created]);
      setComment("");
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <StitchScreen scroll={false} bottom={false}>
        <TopBar title="게시글" back right="more-horiz" />
        <View style={styles.center}>
          <ActivityIndicator color={stitch.blue} />
        </View>
      </StitchScreen>
    );
  }

  if (!post) {
    return (
      <StitchScreen bottom={false}>
        <TopBar title="게시글" back right="more-horiz" />
        <View style={styles.center}>
          <Text style={styles.emptyText}>게시글을 찾을 수 없어요.</Text>
        </View>
      </StitchScreen>
    );
  }

  return (
    <StitchScreen scroll={false} bottom={false}>
      <KeyboardAvoidingView
        style={styles.wrap}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={8}
      >
        <TopBar title="게시글" back right="more-horiz" />
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.authorMeta}>
            <View style={styles.authorRow}>
              <View style={styles.avatar}>
                <MaterialIcons name="person" size={20} color={stitch.blue} />
              </View>
              <View>
                <Text style={styles.author}>{post.anonymous_name || "익명"}</Text>
                <Text style={styles.time}>{post.created_at?.slice(0, 10) || "방금 전"} · 인증 사용자</Text>
              </View>
            </View>
            <Pressable style={styles.followButton}>
              <Text style={styles.followText}>팔로우</Text>
            </Pressable>
          </View>

          <RemoteImage uri={stitchImages.communityHero} style={styles.heroImage} />

          <View style={styles.postBodyBlock}>
            <View style={styles.postTitleRow}>
              <Text style={styles.title}>{post.title}</Text>
              <Pressable style={styles.translateButton}>
                <MaterialIcons name="translate" size={18} color={stitch.blue} />
                <Text style={styles.translateText}>번역 보기</Text>
              </Pressable>
            </View>

            <Text style={styles.body}>{post.content}</Text>

            <View style={styles.tags}>
              <Text style={styles.tag}>#{COMMUNITY_CATEGORY_LABELS[post.category] ?? post.category}</Text>
              <Text style={styles.tag}>#상담준비</Text>
              <Text style={styles.tag}>#자료정리</Text>
            </View>
          </View>

          <View style={styles.socialActions}>
            <View style={styles.socialLeft}>
              <Social icon={post.my_liked ? "favorite" : "favorite-border"} label={String(post.like_count || 0)} active={post.my_liked} />
              <Social icon="chat-bubble-outline" label={String(comments.length || post.comment_count || 0)} />
              <Social icon="share" label="공유" />
            </View>
            <MaterialIcons name="bookmark-border" size={24} color={stitch.outline} />
          </View>

          <View style={styles.commentsHeader}>
            <Text style={styles.commentsTitle}>댓글 <Text style={styles.commentsCount}>({comments.length})</Text></Text>
            <Text style={styles.sortText}>최신순</Text>
          </View>

          <View style={styles.comments}>
            {comments.map((item, index) => (
              <Comment key={item.id} item={item} nested={index === 1} />
            ))}
            {!comments.length ? (
              <Card style={styles.emptyComment}>
                <Text style={styles.emptyText}>첫 댓글을 남겨보세요.</Text>
              </Card>
            ) : null}
          </View>
        </ScrollView>

        <View style={styles.inputPanel}>
          <Card style={styles.inputCard}>
            <TextInput
              value={comment}
              onChangeText={setComment}
              placeholder="댓글 달기"
              placeholderTextColor={stitch.outline}
              style={styles.input}
            />
            <Pressable style={[styles.send, sending && { opacity: 0.5 }]} onPress={sendComment} disabled={sending}>
              <MaterialIcons name="send" size={19} color="#fff" />
            </Pressable>
          </Card>
        </View>
      </KeyboardAvoidingView>
    </StitchScreen>
  );
}

function Social({
  icon,
  label,
  active,
}: {
  icon: keyof typeof MaterialIcons.glyphMap;
  label: string;
  active?: boolean;
}) {
  return (
    <View style={styles.social}>
      <MaterialIcons name={icon} size={22} color={active ? stitch.red : stitch.outline} />
      <Text style={styles.socialText}>{label}</Text>
    </View>
  );
}

function Comment({ item, nested }: { item: CommunityComment; nested?: boolean }) {
  return (
    <View style={[styles.commentRow, nested && styles.nestedComment]}>
      <View style={styles.commentAvatar}>
        <MaterialIcons name="person" size={16} color={stitch.outline} />
      </View>
      <View style={{ flex: 1 }}>
        <View style={styles.commentBubble}>
          <View style={styles.commentTop}>
            <Text style={styles.commentAuthor}>{item.anonymous_name || "익명"}</Text>
            <Text style={styles.commentTime}>{item.created_at?.slice(0, 10) || "방금 전"}</Text>
          </View>
          <Text style={styles.commentText}>{item.content}</Text>
        </View>
        <View style={styles.commentActions}>
          <Text style={styles.commentAction}>좋아요</Text>
          <Text style={styles.commentAction}>답글</Text>
          {item.like_count ? <Text style={styles.commentLikes}>♥ {item.like_count}</Text> : null}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: stitch.bg },
  content: { paddingBottom: 112 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 20 },
  emptyText: { color: stitch.muted, fontSize: 14, fontWeight: "700" },
  authorMeta: { paddingHorizontal: 20, paddingVertical: 14, flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: stitch.surface },
  authorRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  avatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "rgba(198,198,205,0.4)" },
  author: { color: stitch.text, fontSize: 13, fontWeight: "900" },
  time: { marginTop: 2, color: stitch.outline, fontSize: 11, fontWeight: "700" },
  followButton: { height: 34, borderRadius: 17, borderWidth: 1, borderColor: "rgba(0,81,213,0.25)", paddingHorizontal: 16, alignItems: "center", justifyContent: "center" },
  followText: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  heroImage: { width: "100%", height: 430, borderRadius: 0 },
  postBodyBlock: { paddingHorizontal: 20, paddingVertical: 20, gap: 12, backgroundColor: stitch.surface },
  postTitleRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  title: { flex: 1, color: stitch.text, fontSize: 22, lineHeight: 30, fontWeight: "900" },
  translateButton: { flexDirection: "row", alignItems: "center", gap: 4, paddingVertical: 4 },
  translateText: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  body: { color: stitch.muted, fontSize: 14, lineHeight: 22, fontWeight: "600" },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 8, paddingTop: 4 },
  tag: { color: stitch.muted, backgroundColor: stitch.surfaceLow, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, overflow: "hidden", fontSize: 11, fontWeight: "900" },
  socialActions: { paddingHorizontal: 20, paddingVertical: 14, backgroundColor: stitch.surface, borderTopWidth: 1, borderBottomWidth: 1, borderColor: "rgba(198,198,205,0.35)", flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  socialLeft: { flexDirection: "row", gap: 22 },
  social: { flexDirection: "row", alignItems: "center", gap: 5 },
  socialText: { color: stitch.outline, fontSize: 12, fontWeight: "900" },
  commentsHeader: { paddingHorizontal: 20, paddingTop: 20, paddingBottom: 10, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  commentsTitle: { color: stitch.text, fontSize: 20, fontWeight: "900" },
  commentsCount: { color: stitch.outline, fontSize: 15, fontWeight: "700" },
  sortText: { color: stitch.outline, fontSize: 12, fontWeight: "800" },
  comments: { paddingHorizontal: 20, gap: 18 },
  commentRow: { flexDirection: "row", gap: 12 },
  nestedComment: { marginLeft: 38 },
  commentAvatar: { width: 32, height: 32, borderRadius: 16, backgroundColor: stitch.surfaceHigh, alignItems: "center", justifyContent: "center" },
  commentBubble: { backgroundColor: stitch.surfaceLow, borderRadius: 14, borderTopLeftRadius: 3, padding: 12 },
  commentTop: { flexDirection: "row", justifyContent: "space-between", gap: 10, marginBottom: 4 },
  commentAuthor: { color: stitch.text, fontSize: 12, fontWeight: "900" },
  commentTime: { color: stitch.outline, fontSize: 11, fontWeight: "700" },
  commentText: { color: stitch.muted, fontSize: 13, lineHeight: 20, fontWeight: "600" },
  commentActions: { marginTop: 7, marginLeft: 4, flexDirection: "row", gap: 18 },
  commentAction: { color: stitch.outline, fontSize: 11, fontWeight: "900" },
  commentLikes: { color: stitch.outline, fontSize: 11, fontWeight: "900" },
  emptyComment: { padding: 18, alignItems: "center" },
  inputPanel: { position: "absolute", left: 0, right: 0, bottom: 0, padding: 14, backgroundColor: "rgba(247,249,251,0.94)", borderTopWidth: 1, borderTopColor: "rgba(198,198,205,0.35)" },
  inputCard: { minHeight: 54, paddingHorizontal: 12, flexDirection: "row", alignItems: "center", gap: 10 },
  input: { flex: 1, color: stitch.text, fontSize: 14, fontWeight: "700" },
  send: { width: 38, height: 38, borderRadius: 19, backgroundColor: stitch.navy, alignItems: "center", justifyContent: "center" },
});
