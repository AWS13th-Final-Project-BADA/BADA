import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { ApiError } from "@/lib/api";
import type { CommunityPost } from "@/features/community/types";
import {
  listCommunityPosts,
  toggleCommunityReaction,
  translateCommunityTarget,
} from "@/features/community/api";
import {
  CommunityAction,
  communityErrorMessage,
  formatCommunityDate,
} from "@/features/community/ui";
import { Card, Chip, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

const FILTERS = ["all", "free", "wage", "petition", "review"] as const;
type FeedMode = "hot" | "latest" | "mine";

export default function CommunityFeed() {
  const router = useRouter();
  const { locale } = useLocale();
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [mode, setMode] = useState<FeedMode>("hot");
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const response = await listCommunityPosts({
        category: filter,
        sort: mode === "latest" ? "latest" : "hot",
        query: appliedQuery,
        mine: mode === "mine",
      });
      setPosts(response.posts ?? []);
    } catch (nextError) {
      if (nextError instanceof ApiError && nextError.status === 401) {
        router.replace("/login");
        return;
      }
      setError(communityErrorMessage(nextError, t("community.loadError")));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [appliedQuery, filter, mode, router]);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      void load();
    }, [load])
  );

  function search() {
    const next = query.trim();
    if (next === appliedQuery) {
      setLoading(true);
      void load();
      return;
    }
    setAppliedQuery(next);
  }

  function clearSearch() {
    setQuery("");
    setAppliedQuery("");
  }

  function refresh() {
    setRefreshing(true);
    void load();
  }

  async function togglePostReaction(post: CommunityPost, reaction: "like" | "save") {
    const previous = post;
    const activeKey = reaction === "like" ? "my_liked" : "my_saved";
    const countKey = reaction === "like" ? "like_count" : "saved_count";
    const optimisticActive = !post[activeKey];
    const optimisticCount = Math.max(0, post[countKey] + (optimisticActive ? 1 : -1));
    setPosts((items) => items.map((item) => item.id === post.id ? { ...item, [activeKey]: optimisticActive, [countKey]: optimisticCount } : item));

    try {
      const result = await toggleCommunityReaction("post", post.id, reaction);
      setPosts((items) => items.map((item) => item.id === post.id ? {
        ...item,
        [activeKey]: result.active,
        [countKey]: reaction === "like" ? result.like_count ?? item.like_count : result.saved_count ?? item.saved_count,
      } : item));
    } catch (nextError) {
      setPosts((items) => items.map((item) => item.id === post.id ? previous : item));
      Alert.alert(t("community.actionFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    }
  }

  return (
    <StitchScreen scroll={false} active="community">
      <TopBar
        title={t("community.title")}
        right="edit"
        rightLabel={t("community.write")}
        onRightPress={() => router.push("/community/new")}
      />
      <ScrollView
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={stitch.blue} />}
        contentContainerStyle={styles.content}
      >
        <View style={styles.intro}>
          <Text style={styles.introTitle}>{t("community.feedTitle")}</Text>
          <Text style={styles.introBody}>{t("community.subtitle")}</Text>
        </View>

        <View style={styles.controls}>
          <View style={styles.searchBox}>
            <MaterialIcons name="search" size={21} color={stitch.outline} />
            <TextInput
              value={query}
              onChangeText={setQuery}
              onSubmitEditing={search}
              returnKeyType="search"
              placeholder={t("community.search")}
              placeholderTextColor={stitch.outline}
              style={styles.searchInput}
            />
            {query ? (
              <Pressable accessibilityLabel={t("community.clearSearch")} onPress={clearSearch} style={styles.searchIconButton}>
                <MaterialIcons name="cancel" size={19} color={stitch.outline} />
              </Pressable>
            ) : null}
            <Pressable accessibilityLabel={t("common.search")} onPress={search} style={styles.searchButton}>
              <MaterialIcons name="arrow-forward" size={19} color="#fff" />
            </Pressable>
          </View>

          <View style={styles.segmented}>
            {(["hot", "latest", "mine"] as FeedMode[]).map((item) => (
              <Pressable
                key={item}
                onPress={() => setMode(item)}
                style={[styles.segment, mode === item && styles.segmentOn]}
              >
                <Text style={[styles.segmentText, mode === item && styles.segmentTextOn]}>{t(`community.sort.${item}`)}</Text>
              </Pressable>
            ))}
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters}>
            {FILTERS.map((item) => (
              <Pressable key={item} onPress={() => setFilter(item)}>
                <Chip label={t(`community.categories.${item}`)} active={filter === item} />
              </Pressable>
            ))}
          </ScrollView>
        </View>

        <View style={styles.feed}>
          {appliedQuery ? (
            <View style={styles.resultHeader}>
              <Text style={styles.resultText}>{t("community.searchResult")} “{appliedQuery}”</Text>
              <Text style={styles.resultCount}>{posts.length}</Text>
            </View>
          ) : null}

          {loading ? (
            <View style={styles.loading}>
              <ActivityIndicator color={stitch.blue} />
              <Text style={styles.loadingText}>{t("common.loading")}</Text>
            </View>
          ) : null}

          {!loading && error ? (
            <Card style={styles.stateCard}>
              <View style={styles.stateIconError}><MaterialIcons name="wifi-off" size={23} color={stitch.red} /></View>
              <Text style={styles.stateTitle}>{t("community.loadError")}</Text>
              <Text style={styles.stateBody}>{error}</Text>
              <Pressable style={styles.retryButton} onPress={() => void load()}>
                <Text style={styles.retryText}>{t("community.retry")}</Text>
              </Pressable>
            </Card>
          ) : null}

          {!loading && !error && posts.length === 0 ? (
            <Card style={styles.stateCard}>
              <View style={styles.stateIcon}><MaterialIcons name={mode === "mine" ? "person-outline" : "forum"} size={25} color={stitch.blue} /></View>
              <Text style={styles.stateTitle}>{mode === "mine" ? t("community.myEmptyTitle") : t("community.emptyTitle")}</Text>
              <Text style={styles.stateBody}>{mode === "mine" ? t("community.myEmptyBody") : t("community.emptyBody")}</Text>
              <Pressable style={styles.writeEmptyButton} onPress={() => router.push("/community/new")}>
                <MaterialIcons name="edit" size={17} color="#fff" />
                <Text style={styles.writeEmptyText}>{t("community.write")}</Text>
              </Pressable>
            </Card>
          ) : null}

          {!loading && !error ? posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              locale={locale}
              onOpen={() => router.push({ pathname: "/community/[id]", params: { id: post.id } })}
              onLike={() => void togglePostReaction(post, "like")}
              onSave={() => void togglePostReaction(post, "save")}
            />
          )) : null}
        </View>
      </ScrollView>

      <Pressable style={styles.fab} onPress={() => router.push("/community/new")} accessibilityLabel={t("community.write")}>
        <MaterialIcons name="edit" size={20} color="#fff" />
        <Text style={styles.fabText}>{t("community.write")}</Text>
      </Pressable>
    </StitchScreen>
  );
}

function PostCard({
  post,
  locale,
  onOpen,
  onLike,
  onSave,
}: {
  post: CommunityPost;
  locale: string;
  onOpen: () => void;
  onLike: () => void;
  onSave: () => void;
}) {
  const [translation, setTranslation] = useState("");
  const [translationVisible, setTranslationVisible] = useState(false);
  const [translating, setTranslating] = useState(false);
  const canTranslate = Boolean(post.language_code && post.language_code !== locale);

  async function toggleTranslation() {
    if (translation) {
      setTranslationVisible((value) => !value);
      return;
    }
    setTranslating(true);
    try {
      const result = await translateCommunityTarget("post", post.id, locale);
      setTranslation(result.translated_text);
      setTranslationVisible(true);
    } catch (nextError) {
      Alert.alert(t("community.translationFailed"), communityErrorMessage(nextError, t("community.tryAgain")));
    } finally {
      setTranslating(false);
    }
  }

  return (
    <Pressable onPress={onOpen} style={({ pressed }) => pressed && { opacity: 0.94 }}>
      <Card style={styles.post}>
        <View style={styles.postTop}>
          <View style={styles.authorRow}>
            <View style={styles.avatar}><MaterialIcons name="person" size={18} color={stitch.blue} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.author} numberOfLines={1}>{post.anonymous_name || t("community.anonymous")}</Text>
              <View style={styles.metaRow}>
                <Text style={styles.time}>{formatCommunityDate(post.created_at, locale)}</Text>
                {post.language_code ? <Text style={styles.language}>{post.language_code.toUpperCase()}</Text> : null}
              </View>
            </View>
          </View>
          <View style={styles.categoryPill}><Text style={styles.categoryText}>{t(`community.categories.${post.category}`)}</Text></View>
        </View>

        <Text style={styles.postTitle}>{post.title}</Text>
        <Text style={styles.postBody} numberOfLines={translationVisible ? undefined : 4}>{translationVisible ? translation : post.content}</Text>

        {translationVisible ? <Text style={styles.translationNotice}>{t("community.translationNotice")}</Text> : null}

        <View style={styles.actionRow}>
          <View style={styles.leftActions}>
            <CommunityAction icon={post.my_liked ? "favorite" : "favorite-border"} label={String(post.like_count || 0)} active={post.my_liked} onPress={onLike} />
            <CommunityAction icon="chat-bubble-outline" label={String(post.comment_count || 0)} onPress={onOpen} />
            {canTranslate ? (
              <CommunityAction
                icon="translate"
                label={translating ? t("community.translating") : translationVisible ? t("community.original") : t("community.translate")}
                active={translationVisible}
                onPress={() => void toggleTranslation()}
                disabled={translating}
              />
            ) : null}
          </View>
          <CommunityAction icon={post.my_saved ? "bookmark" : "bookmark-border"} label={String(post.saved_count || 0)} active={post.my_saved} onPress={onSave} />
        </View>
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: 136 },
  intro: { paddingHorizontal: 20, paddingTop: 20, paddingBottom: 14 },
  introTitle: { color: stitch.text, fontSize: 24, lineHeight: 32, fontWeight: "900" },
  introBody: { marginTop: 5, color: stitch.muted, fontSize: 14, lineHeight: 21, fontWeight: "600" },
  controls: { paddingHorizontal: 20, paddingBottom: 14, gap: 12 },
  searchBox: { height: 50, borderRadius: 12, backgroundColor: stitch.surface, borderWidth: 1, borderColor: "rgba(198,198,205,0.7)", paddingLeft: 13, paddingRight: 5, flexDirection: "row", alignItems: "center", gap: 9 },
  searchInput: { flex: 1, minWidth: 0, color: stitch.text, fontSize: 14, fontWeight: "700" },
  searchIconButton: { width: 32, height: 40, alignItems: "center", justifyContent: "center" },
  searchButton: { width: 40, height: 40, borderRadius: 10, backgroundColor: stitch.navy, alignItems: "center", justifyContent: "center" },
  segmented: { height: 42, padding: 3, borderRadius: 11, backgroundColor: stitch.surfaceHigh, flexDirection: "row" },
  segment: { flex: 1, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  segmentOn: { backgroundColor: stitch.surface, shadowColor: "#0f172a", shadowOpacity: 0.06, shadowRadius: 5, elevation: 1 },
  segmentText: { color: stitch.outline, fontSize: 12, fontWeight: "800" },
  segmentTextOn: { color: stitch.text },
  filters: { gap: 8, paddingRight: 20 },
  feed: { paddingHorizontal: 20, gap: 14 },
  resultHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 2 },
  resultText: { flex: 1, color: stitch.muted, fontSize: 12, fontWeight: "700" },
  resultCount: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  loading: { paddingVertical: 36, alignItems: "center", gap: 9 },
  loadingText: { color: stitch.outline, fontSize: 12, fontWeight: "700" },
  stateCard: { padding: 26, alignItems: "center" },
  stateIcon: { width: 50, height: 50, borderRadius: 25, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center", marginBottom: 12 },
  stateIconError: { width: 50, height: 50, borderRadius: 25, backgroundColor: stitch.redSoft, alignItems: "center", justifyContent: "center", marginBottom: 12 },
  stateTitle: { color: stitch.text, fontSize: 17, fontWeight: "900", textAlign: "center" },
  stateBody: { marginTop: 6, color: stitch.muted, fontSize: 13, lineHeight: 19, fontWeight: "600", textAlign: "center" },
  retryButton: { marginTop: 15, minHeight: 42, paddingHorizontal: 20, borderRadius: 9, backgroundColor: stitch.surfaceLow, alignItems: "center", justifyContent: "center" },
  retryText: { color: stitch.text, fontSize: 13, fontWeight: "800" },
  writeEmptyButton: { marginTop: 16, minHeight: 44, paddingHorizontal: 18, borderRadius: 10, backgroundColor: stitch.navy, flexDirection: "row", alignItems: "center", gap: 7 },
  writeEmptyText: { color: "#fff", fontSize: 13, fontWeight: "900" },
  post: { paddingTop: 15, overflow: "hidden" },
  postTop: { paddingHorizontal: 16, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  authorRow: { flex: 1, minWidth: 0, flexDirection: "row", alignItems: "center", gap: 10 },
  avatar: { width: 36, height: 36, borderRadius: 18, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  author: { color: stitch.text, fontSize: 13, fontWeight: "900" },
  metaRow: { marginTop: 2, flexDirection: "row", alignItems: "center", gap: 7 },
  time: { color: stitch.outline, fontSize: 11, fontWeight: "700" },
  language: { color: stitch.outline, fontSize: 10, fontWeight: "800" },
  categoryPill: { paddingHorizontal: 9, paddingVertical: 5, borderRadius: 999, backgroundColor: stitch.greenSoft },
  categoryText: { color: stitch.green, fontSize: 10, fontWeight: "900" },
  postTitle: { paddingHorizontal: 16, marginTop: 14, color: stitch.text, fontSize: 18, lineHeight: 25, fontWeight: "900" },
  postBody: { paddingHorizontal: 16, marginTop: 7, color: stitch.muted, fontSize: 14, lineHeight: 21, fontWeight: "600" },
  translationNotice: { paddingHorizontal: 16, marginTop: 7, color: stitch.blue, fontSize: 10, fontWeight: "700" },
  actionRow: { minHeight: 54, marginTop: 13, paddingHorizontal: 11, borderTopWidth: 1, borderTopColor: "rgba(198,198,205,0.3)", flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  leftActions: { flexDirection: "row", alignItems: "center", gap: 7 },
  fab: { position: "absolute", right: 20, bottom: 92, minHeight: 50, borderRadius: 25, paddingHorizontal: 17, backgroundColor: stitch.navy, flexDirection: "row", alignItems: "center", gap: 8, shadowColor: "#0f172a", shadowOpacity: 0.2, shadowRadius: 11, shadowOffset: { width: 0, height: 7 }, elevation: 8 },
  fabText: { color: "#fff", fontSize: 14, fontWeight: "900" },
});