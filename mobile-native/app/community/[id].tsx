import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import type { CommunityComment, CommunityPost } from "@/features/community/types";
import {
  checkCommunitySafety,
  createCommunityComment,
  deleteCommunityComment,
  deleteCommunityPost,
  getCommunityPost,
  listCommunityComments,
  reportCommunityTarget,
  toggleCommunityReaction,
  translateCommunityTarget,
  updateCommunityComment,
} from "@/features/community/api";
import type { CommunityTargetType } from "@/features/community/api";
import {
  CommunityAction,
  CommunityMenuSheet,
  CommunityReportSheet,
  communityErrorMessage,
  formatCommunityDate,
  type CommunityMenuOption,
} from "@/features/community/ui";
import { Card, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

interface ReportTarget {
  type: CommunityTargetType;
  id: string;
}

export default function CommunityPostDetail() {
  const params = useLocalSearchParams<{ id?: string }>();
  const router = useRouter();
  const { locale } = useLocale();
  const postId = typeof params.id === "string" ? params.id : "";
  const inputRef = useRef<TextInput>(null);
  const [post, setPost] = useState<CommunityPost | null>(null);
  const [comments, setComments] = useState<CommunityComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [comment, setComment] = useState("");
  const [replyTo, setReplyTo] = useState<CommunityComment | null>(null);
  const [sending, setSending] = useState(false);
  const [postTranslation, setPostTranslation] = useState<{ title: string; content: string } | null>(null);
  const [postTranslationVisible, setPostTranslationVisible] = useState(false);
  const [translatingPost, setTranslatingPost] = useState(false);
  const [commentTranslations, setCommentTranslations] = useState<Record<string, string>>({});
  const [translatingCommentId, setTranslatingCommentId] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [reportTarget, setReportTarget] = useState<ReportTarget | null>(null);
  const [reporting, setReporting] = useState(false);
  const [editingComment, setEditingComment] = useState<CommunityComment | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editingBusy, setEditingBusy] = useState(false);

  const load = useCallback(async () => {
    if (!postId) {
      setError(t("community.notFound"));
      setLoading(false);
      return;
    }
    setError("");
    try {
      const [nextPost, nextComments] = await Promise.all([
        getCommunityPost(postId),
        listCommunityComments(postId),
      ]);
      setPost(nextPost);
      setComments(nextComments.comments ?? []);
    } catch (nextError) {
      setError(communityErrorMessage(nextError, t("community.loadError")));
    } finally {
      setLoading(false);
    }
  }, [postId]);

  useEffect(() => { void load(); }, [load]);

  async function togglePostReaction(reaction: "like" | "save") {
    if (!post) return;
    const previous = post;
    const activeKey = reaction === "like" ? "my_liked" : "my_saved";
    const countKey = reaction === "like" ? "like_count" : "saved_count";
    const active = !post[activeKey];
    setPost({ ...post, [activeKey]: active, [countKey]: Math.max(0, post[countKey] + (active ? 1 : -1)) });
    try {
      const result = await toggleCommunityReaction("post", post.id, reaction);
      setPost((current) => current ? {
        ...current,
        [activeKey]: result.active,
        [countKey]: reaction === "like" ? result.like_count ?? current.like_count : result.saved_count ?? current.saved_count,
      } : current);
    } catch (nextError) {
      setPost(previous);
      Alert.alert(t("community.actionFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    }
  }

  async function togglePostTranslation() {
    if (!post) return;
    if (postTranslation) {
      setPostTranslationVisible((value) => !value);
      return;
    }
    setTranslatingPost(true);
    try {
      const result = await translateCommunityTarget("post", post.id, locale);
      setPostTranslation({
        title: result.translated_title || post.title,
        content: result.translated_content || result.translated_text,
      });
      setPostTranslationVisible(true);
    } catch (nextError) {
      Alert.alert(t("community.translationFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    } finally {
      setTranslatingPost(false);
    }
  }

  async function sharePost() {
    if (!post) return;
    try {
      await Share.share({ message: `${post.title}\n\n${post.content}\n\nBADA` });
    } catch {
      Alert.alert(t("community.actionFailed"), t("community.tryAgain"));
    }
  }

  function confirmDeletePost() {
    if (!post) return;
    Alert.alert(t("community.deletePostTitle"), t("community.deletePostBody"), [
      { text: t("common.cancel"), style: "cancel" },
      {
        text: t("common.delete"),
        style: "destructive",
        onPress: () => {
          void deleteCommunityPost(post.id)
            .then(() => router.replace("/community"))
            .catch((nextError) => Alert.alert(t("community.deleteFailed"), communityErrorMessage(nextError, t("community.tryAgain"))));
        },
      },
    ]);
  }

  function postMenuOptions(): CommunityMenuOption[] {
    if (!post) return [];
    if (post.my_owned) {
      return [
        { key: "edit", label: t("community.editPost"), icon: "edit", onPress: () => router.push({ pathname: "/community/new", params: { id: post.id } }) },
        { key: "delete", label: t("community.deletePost"), icon: "delete-outline", danger: true, onPress: confirmDeletePost },
      ];
    }
    return [{ key: "report", label: t("community.report"), icon: "flag", danger: true, onPress: () => setReportTarget({ type: "post", id: post.id }) }];
  }

  async function sendComment() {
    const text = comment.trim();
    if (!text || sending || !post) return;
    setSending(true);
    try {
      const safety = await checkCommunitySafety(text, locale);
      if (!safety.allowed) {
        Alert.alert(t("community.safetyBlocked"), safety.message || t("community.blocked"));
        return;
      }
      const created = await createCommunityComment(post.id, { content: text, language: locale, parent_comment_id: replyTo?.id ?? null });
      setComments((items) => [...items, created]);
      setPost((current) => current ? { ...current, comment_count: current.comment_count + 1 } : current);
      setComment("");
      setReplyTo(null);
    } catch (nextError) {
      Alert.alert(t("community.commentFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    } finally {
      setSending(false);
    }
  }

  async function toggleCommentLike(item: CommunityComment) {
    const previous = item;
    const active = !item.my_liked;
    setComments((items) => items.map((commentItem) => commentItem.id === item.id ? { ...commentItem, my_liked: active, like_count: Math.max(0, commentItem.like_count + (active ? 1 : -1)) } : commentItem));
    try {
      const result = await toggleCommunityReaction("comment", item.id, "like");
      setComments((items) => items.map((commentItem) => commentItem.id === item.id ? { ...commentItem, my_liked: result.active, like_count: result.like_count ?? commentItem.like_count } : commentItem));
    } catch (nextError) {
      setComments((items) => items.map((commentItem) => commentItem.id === item.id ? previous : commentItem));
      Alert.alert(t("community.actionFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    }
  }

  async function toggleCommentTranslation(item: CommunityComment) {
    if (commentTranslations[item.id]) {
      setCommentTranslations((items) => ({ ...items, [item.id]: "" }));
      return;
    }
    setTranslatingCommentId(item.id);
    try {
      const result = await translateCommunityTarget("comment", item.id, locale);
      setCommentTranslations((items) => ({ ...items, [item.id]: result.translated_text }));
    } catch (nextError) {
      Alert.alert(t("community.translationFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    } finally {
      setTranslatingCommentId("");
    }
  }

  function startReply(item: CommunityComment) {
    setReplyTo(item);
    inputRef.current?.focus();
  }

  function startEditComment(item: CommunityComment) {
    setEditingComment(item);
    setEditValue(item.content);
  }

  async function saveEditedComment() {
    if (!editingComment || editValue.trim().length < 1) return;
    setEditingBusy(true);
    try {
      const safety = await checkCommunitySafety(editValue.trim(), locale);
      if (!safety.allowed) {
        Alert.alert(t("community.safetyBlocked"), safety.message || t("community.blocked"));
        return;
      }
      const updated = await updateCommunityComment(editingComment.id, { content: editValue.trim(), language: locale });
      setComments((items) => items.map((item) => item.id === updated.id ? updated : item));
      setEditingComment(null);
      setEditValue("");
    } catch (nextError) {
      Alert.alert(t("community.updateFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    } finally {
      setEditingBusy(false);
    }
  }

  function confirmDeleteComment(item: CommunityComment) {
    Alert.alert(t("community.deleteCommentTitle"), t("community.deleteCommentBody"), [
      { text: t("common.cancel"), style: "cancel" },
      {
        text: t("common.delete"),
        style: "destructive",
        onPress: () => {
          void deleteCommunityComment(item.id)
            .then(() => {
              setComments((items) => items.filter((commentItem) => commentItem.id !== item.id));
              setPost((current) => current ? { ...current, comment_count: Math.max(0, current.comment_count - 1) } : current);
            })
            .catch((nextError) => Alert.alert(t("community.deleteFailed"), communityErrorMessage(nextError, t("community.tryAgain"))));
        },
      },
    ]);
  }

  async function submitReport(reason: string, description: string) {
    if (!reportTarget) return;
    setReporting(true);
    try {
      await reportCommunityTarget(reportTarget.type, reportTarget.id, reason, description || undefined);
      setReportTarget(null);
      Alert.alert(t("community.reportCompleteTitle"), t("community.reportCompleteBody"));
    } catch (nextError) {
      Alert.alert(t("community.reportFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    } finally {
      setReporting(false);
    }
  }

  if (loading) {
    return <StitchScreen scroll={false} bottom={false}><TopBar title={t("community.title")} back right="more-horiz" /><View style={styles.center}><ActivityIndicator color={stitch.blue} /></View></StitchScreen>;
  }

  if (!post || error) {
    return (
      <StitchScreen scroll={false} bottom={false}>
        <TopBar title={t("community.title")} back />
        <View style={styles.center}>
          <View style={styles.errorIcon}><MaterialIcons name="error-outline" size={26} color={stitch.red} /></View>
          <Text style={styles.emptyTitle}>{t("community.notFound")}</Text>
          <Text style={styles.emptyText}>{error || t("community.loadError")}</Text>
          <Pressable style={styles.retryButton} onPress={() => { setLoading(true); void load(); }}><Text style={styles.retryText}>{t("community.retry")}</Text></Pressable>
        </View>
      </StitchScreen>
    );
  }

  const canTranslatePost = Boolean(post.language_code && post.language_code !== locale);

  return (
    <StitchScreen scroll={false} bottom={false}>
      <KeyboardAvoidingView style={styles.wrap} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={8}>
        <TopBar title={t("community.title")} back right="more-horiz" rightLabel={t("community.moreActions")} onRightPress={() => setMenuOpen(true)} />
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
          <View style={styles.postSection}>
            <View style={styles.authorMeta}>
              <View style={styles.avatar}><MaterialIcons name="person" size={20} color={stitch.blue} /></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.author}>{post.anonymous_name || t("community.anonymous")}</Text>
                <View style={styles.metaRow}>
                  <Text style={styles.time}>{formatCommunityDate(post.created_at, locale)}</Text>
                  {post.language_code ? <Text style={styles.language}>{post.language_code.toUpperCase()}</Text> : null}
                </View>
              </View>
              <View style={styles.categoryPill}><Text style={styles.categoryText}>{t(`community.categories.${post.category}`)}</Text></View>
            </View>
            <Text style={styles.title}>{postTranslationVisible && postTranslation ? postTranslation.title : post.title}</Text>
            <Text style={styles.body}>{postTranslationVisible && postTranslation ? postTranslation.content : post.content}</Text>
            {postTranslationVisible ? <Text style={styles.translationNotice}>{t("community.translationNotice")}</Text> : null}
            <View style={styles.postUtilityRow}>
              {canTranslatePost ? <CommunityAction icon="translate" label={translatingPost ? t("community.translating") : postTranslationVisible ? t("community.original") : t("community.translate")} active={postTranslationVisible} disabled={translatingPost} onPress={() => void togglePostTranslation()} /> : <View />}
              {post.my_owned ? <Text style={styles.ownerBadge}>{t("community.myPost")}</Text> : null}
            </View>
          </View>

          <View style={styles.socialActions}>
            <View style={styles.socialLeft}>
              <CommunityAction icon={post.my_liked ? "favorite" : "favorite-border"} label={String(post.like_count || 0)} active={post.my_liked} onPress={() => void togglePostReaction("like")} />
              <CommunityAction icon="chat-bubble-outline" label={String(comments.length)} onPress={() => inputRef.current?.focus()} />
              <CommunityAction icon="share" label={t("community.share")} onPress={() => void sharePost()} />
            </View>
            <CommunityAction icon={post.my_saved ? "bookmark" : "bookmark-border"} label={String(post.saved_count || 0)} active={post.my_saved} onPress={() => void togglePostReaction("save")} />
          </View>

          <View style={styles.commentsHeader}><Text style={styles.commentsTitle}>{t("community.comments")}</Text><Text style={styles.commentsCount}>{comments.length}</Text></View>
          <View style={styles.comments}>
            {comments.map((item) => (
              <CommentRow key={item.id} item={item} locale={locale} translatedText={commentTranslations[item.id]} translating={translatingCommentId === item.id} onLike={() => void toggleCommentLike(item)} onTranslate={() => void toggleCommentTranslation(item)} onReply={() => startReply(item)} onEdit={() => startEditComment(item)} onDelete={() => confirmDeleteComment(item)} onReport={() => setReportTarget({ type: "comment", id: item.id })} />
            ))}
            {!comments.length ? <Card style={styles.emptyComment}><View style={styles.commentEmptyIcon}><MaterialIcons name="chat-bubble-outline" size={22} color={stitch.blue} /></View><Text style={styles.emptyTitle}>{t("community.noCommentsTitle")}</Text><Text style={styles.emptyText}>{t("community.noCommentsBody")}</Text></Card> : null}
          </View>
        </ScrollView>

        <View style={styles.inputPanel}>
          {replyTo ? <View style={styles.replyBanner}><MaterialIcons name="reply" size={16} color={stitch.blue} /><Text style={styles.replyText} numberOfLines={1}>{replyTo.anonymous_name}{t("community.replyingTo")}</Text><Pressable onPress={() => setReplyTo(null)}><MaterialIcons name="close" size={18} color={stitch.outline} /></Pressable></View> : null}
          <View style={styles.inputCard}>
            <TextInput ref={inputRef} value={comment} onChangeText={setComment} placeholder={replyTo ? t("community.replyPlaceholder") : t("community.commentPlaceholder")} placeholderTextColor={stitch.outline} style={styles.input} multiline maxLength={2000} />
            <Pressable style={[styles.send, (!comment.trim() || sending) && styles.sendDisabled]} onPress={() => void sendComment()} disabled={!comment.trim() || sending}>{sending ? <ActivityIndicator size="small" color="#fff" /> : <MaterialIcons name="send" size={19} color="#fff" />}</Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>

      <CommunityMenuSheet visible={menuOpen} title={t("community.postOptions")} options={postMenuOptions()} onClose={() => setMenuOpen(false)} />
      <CommunityReportSheet visible={Boolean(reportTarget)} busy={reporting} onClose={() => setReportTarget(null)} onSubmit={(reason, description) => void submitReport(reason, description)} />
      <CommentEditorModal visible={Boolean(editingComment)} value={editValue} busy={editingBusy} onChange={setEditValue} onClose={() => setEditingComment(null)} onSave={() => void saveEditedComment()} />
    </StitchScreen>
  );
}

function CommentRow({ item, locale, translatedText, translating, onLike, onTranslate, onReply, onEdit, onDelete, onReport }: { item: CommunityComment; locale: string; translatedText?: string; translating: boolean; onLike: () => void; onTranslate: () => void; onReply: () => void; onEdit: () => void; onDelete: () => void; onReport: () => void }) {
  const canTranslate = Boolean(item.language_code && item.language_code !== locale);
  return (
    <View style={[styles.commentRow, Boolean(item.parent_comment_id) && styles.nestedComment]}>
      <View style={styles.commentAvatar}><MaterialIcons name="person" size={16} color={stitch.outline} /></View>
      <View style={{ flex: 1, minWidth: 0 }}>
        <View style={styles.commentTop}><View style={{ flex: 1 }}><Text style={styles.commentAuthor}>{item.anonymous_name || t("community.anonymous")}</Text><Text style={styles.commentTime}>{formatCommunityDate(item.created_at, locale)}</Text></View>{item.my_owned ? <Text style={styles.ownerLabel}>{t("community.mine")}</Text> : null}</View>
        <Text style={styles.commentText}>{translatedText || item.content}</Text>
        {translatedText ? <Text style={styles.translationNotice}>{t("community.translationNotice")}</Text> : null}
        <View style={styles.commentActions}>
          <CommunityAction icon={item.my_liked ? "favorite" : "favorite-border"} label={String(item.like_count || 0)} active={item.my_liked} onPress={onLike} />
          <CommunityAction icon="reply" label={t("community.reply")} onPress={onReply} />
          {canTranslate ? <CommunityAction icon="translate" label={translating ? t("community.translating") : translatedText ? t("community.original") : t("community.translate")} active={Boolean(translatedText)} disabled={translating} onPress={onTranslate} /> : null}
          {item.my_owned ? <><CommunityAction icon="edit" label={t("community.edit")} onPress={onEdit} /><CommunityAction icon="delete-outline" label={t("common.delete")} danger onPress={onDelete} /></> : <CommunityAction icon="flag" label={t("community.report")} danger onPress={onReport} />}
        </View>
      </View>
    </View>
  );
}

function CommentEditorModal({ visible, value, busy, onChange, onClose, onSave }: { visible: boolean; value: string; busy: boolean; onChange: (value: string) => void; onClose: () => void; onSave: () => void }) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <KeyboardAvoidingView style={styles.modalOverlay} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={styles.editorModal}>
          <View style={styles.editorTop}><Text style={styles.editorTitle}>{t("community.editComment")}</Text><Pressable onPress={onClose}><MaterialIcons name="close" size={22} color={stitch.outline} /></Pressable></View>
          <TextInput value={value} onChangeText={onChange} multiline maxLength={2000} style={styles.editorInput} />
          <Pressable disabled={busy || !value.trim()} onPress={onSave} style={[styles.editorSave, (busy || !value.trim()) && { opacity: 0.5 }]}>{busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.editorSaveText}>{t("common.save")}</Text>}</Pressable>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: stitch.bg },
  content: { paddingBottom: 132 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 28 },
  errorIcon: { width: 52, height: 52, borderRadius: 26, backgroundColor: stitch.redSoft, alignItems: "center", justifyContent: "center", marginBottom: 12 },
  emptyTitle: { color: stitch.text, fontSize: 16, fontWeight: "900", textAlign: "center" },
  emptyText: { marginTop: 5, color: stitch.muted, fontSize: 13, lineHeight: 19, fontWeight: "600", textAlign: "center" },
  retryButton: { marginTop: 15, minHeight: 42, paddingHorizontal: 18, borderRadius: 9, backgroundColor: stitch.surfaceHigh, justifyContent: "center" },
  retryText: { color: stitch.text, fontSize: 13, fontWeight: "800" },
  postSection: { padding: 20, backgroundColor: stitch.surface },
  authorMeta: { flexDirection: "row", alignItems: "center", gap: 11 },
  avatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  author: { color: stitch.text, fontSize: 13, fontWeight: "900" },
  metaRow: { marginTop: 2, flexDirection: "row", gap: 7 },
  time: { color: stitch.outline, fontSize: 11, fontWeight: "700" },
  language: { color: stitch.outline, fontSize: 10, fontWeight: "800" },
  categoryPill: { paddingHorizontal: 9, paddingVertical: 5, borderRadius: 999, backgroundColor: stitch.greenSoft },
  categoryText: { color: stitch.green, fontSize: 10, fontWeight: "900" },
  title: { marginTop: 20, color: stitch.text, fontSize: 22, lineHeight: 30, fontWeight: "900" },
  body: { marginTop: 11, color: stitch.muted, fontSize: 15, lineHeight: 24, fontWeight: "600" },
  translationNotice: { marginTop: 6, color: stitch.blue, fontSize: 10, fontWeight: "700" },
  postUtilityRow: { minHeight: 42, marginTop: 14, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  ownerBadge: { color: stitch.blue, backgroundColor: stitch.blueSoft, paddingHorizontal: 9, paddingVertical: 5, borderRadius: 999, overflow: "hidden", fontSize: 10, fontWeight: "900" },
  socialActions: { minHeight: 58, paddingHorizontal: 14, backgroundColor: stitch.surface, borderTopWidth: 1, borderBottomWidth: 1, borderColor: "rgba(198,198,205,0.35)", flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  socialLeft: { flexDirection: "row", alignItems: "center", gap: 8 },
  commentsHeader: { paddingHorizontal: 20, paddingTop: 22, paddingBottom: 12, flexDirection: "row", alignItems: "center", gap: 7 },
  commentsTitle: { color: stitch.text, fontSize: 18, fontWeight: "900" },
  commentsCount: { color: stitch.blue, fontSize: 13, fontWeight: "900" },
  comments: { paddingHorizontal: 20, gap: 18 },
  commentRow: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  nestedComment: { marginLeft: 30, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: stitch.blueSoft },
  commentAvatar: { width: 32, height: 32, borderRadius: 16, backgroundColor: stitch.surfaceHigh, alignItems: "center", justifyContent: "center" },
  commentTop: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 10 },
  commentAuthor: { color: stitch.text, fontSize: 12, fontWeight: "900" },
  commentTime: { marginTop: 2, color: stitch.outline, fontSize: 10, fontWeight: "700" },
  ownerLabel: { color: stitch.blue, fontSize: 10, fontWeight: "900" },
  commentText: { marginTop: 7, color: stitch.muted, fontSize: 13, lineHeight: 20, fontWeight: "600" },
  commentActions: { marginTop: 5, marginLeft: -5, flexDirection: "row", alignItems: "center", flexWrap: "wrap", columnGap: 5 },
  emptyComment: { padding: 24, alignItems: "center" },
  commentEmptyIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center", marginBottom: 10 },
  inputPanel: { position: "absolute", left: 0, right: 0, bottom: 0, paddingHorizontal: 14, paddingTop: 9, paddingBottom: 12, backgroundColor: "rgba(247,249,251,0.97)", borderTopWidth: 1, borderTopColor: "rgba(198,198,205,0.45)" },
  replyBanner: { minHeight: 28, paddingHorizontal: 7, flexDirection: "row", alignItems: "center", gap: 6 },
  replyText: { flex: 1, color: stitch.blue, fontSize: 11, fontWeight: "700" },
  inputCard: { minHeight: 52, borderRadius: 14, borderWidth: 1, borderColor: "rgba(198,198,205,0.65)", backgroundColor: stitch.surface, paddingLeft: 13, paddingRight: 6, flexDirection: "row", alignItems: "center", gap: 8 },
  input: { flex: 1, maxHeight: 90, paddingVertical: 10, color: stitch.text, fontSize: 14, lineHeight: 20, fontWeight: "600" },
  send: { width: 40, height: 40, borderRadius: 20, backgroundColor: stitch.navy, alignItems: "center", justifyContent: "center" },
  sendDisabled: { backgroundColor: stitch.outline, opacity: 0.55 },
  modalOverlay: { flex: 1, justifyContent: "center", padding: 20, backgroundColor: "rgba(15,23,42,0.38)" },
  editorModal: { borderRadius: 16, padding: 18, backgroundColor: stitch.surface },
  editorTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  editorTitle: { color: stitch.text, fontSize: 18, fontWeight: "900" },
  editorInput: { minHeight: 130, marginTop: 14, borderRadius: 10, borderWidth: 1, borderColor: stitch.line, padding: 12, color: stitch.text, fontSize: 14, lineHeight: 21, textAlignVertical: "top" },
  editorSave: { height: 48, borderRadius: 10, marginTop: 13, backgroundColor: stitch.navy, alignItems: "center", justifyContent: "center" },
  editorSaveText: { color: "#fff", fontSize: 14, fontWeight: "900" },
});