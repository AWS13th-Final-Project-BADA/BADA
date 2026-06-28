import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
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
import { fetchApi, ApiError } from "@/lib/api";
import type { CommunityPost } from "@/lib/types";
import { COMMUNITY_CATEGORY_LABELS } from "@/lib/types";
import { Card, Chip, RemoteImage, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { stitchImages } from "@/lib/stitchAssets";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";

const FILTERS = ["all", "free", "wage", "petition", "review"] as const;

export default function CommunityFeed() {
  const router = useRouter();
  const { locale } = useLocale();
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async (cat = filter) => {
      try {
        const qs = cat === "all" ? "" : `?category=${cat}`;
        const res = await fetchApi<{ posts: CommunityPost[] }>(`/community/posts${qs}`);
        setPosts(res.posts ?? []);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [filter, router]
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  const visiblePosts = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return posts;
    return posts.filter((post) =>
      `${post.title} ${post.content} ${post.anonymous_name}`.toLowerCase().includes(q)
    );
  }, [posts, query]);

  function refresh() {
    setRefreshing(true);
    void load();
  }

  return (
    <StitchScreen scroll={false} active="community">
      <TopBar title={t("community.title")} right="add-circle-outline" />
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
        contentContainerStyle={styles.content}
      >
        <View style={styles.stickyArea}>
          <View style={styles.searchBox}>
            <MaterialIcons name="search" size={22} color={stitch.outline} />
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder={t("community.search")}
              placeholderTextColor={stitch.outline}
              style={styles.searchInput}
            />
            <Pressable style={styles.tuneButton}>
              <MaterialIcons name="tune" size={20} color={stitch.muted} />
            </Pressable>
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters}>
            {FILTERS.map((item) => {
              const active = filter === item;
              const label = item === "all" ? t("community.categories.all") : (t("community.categories." + item) || COMMUNITY_CATEGORY_LABELS[item]);
              return (
                <Pressable
                  key={item}
                  onPress={() => {
                    setFilter(item);
                    setLoading(true);
                    void load(item);
                  }}
                >
                  <Chip label={label} active={active} />
                </Pressable>
              );
            })}
          </ScrollView>
        </View>

        <View style={styles.feed}>
          {loading ? <ActivityIndicator color={stitch.blue} style={{ marginTop: 24 }} /> : null}

          {!loading && visiblePosts.length === 0 ? (
            <Card style={styles.empty}>
              <MaterialIcons name="forum" size={34} color={stitch.outline} />
              <Text style={styles.emptyTitle}>{t("community.emptyTitle")}</Text>
              <Text style={styles.emptyBody}>{t("community.emptyBody")}</Text>
            </Card>
          ) : null}

          {visiblePosts.map((post, index) => (
            <PostCard
              key={post.id}
              post={post}
              image={index % 2 === 0 ? stitchImages.communityDoc : stitchImages.paycheck}
              onPress={() => router.push({ pathname: "/community/[id]", params: { id: post.id } })}
            />
          ))}
        </View>
      </ScrollView>

      <Pressable style={styles.fab} onPress={() => router.push("/community/new")}>
        <MaterialIcons name="edit" size={20} color="#fff" />
        <Text style={styles.fabText}>{t("community.write")}</Text>
      </Pressable>
    </StitchScreen>
  );
}

function PostCard({
  post,
  image,
  onPress,
}: {
  post: CommunityPost;
  image: string;
  onPress: () => void;
}) {
  const { locale } = useLocale();
  const [translated, setTranslated] = useState<{ title?: string; content?: string } | null>(null);
  const [translating, setTranslating] = useState(false);

  const needsTranslation = locale !== "ko" && !translated;

  useEffect(() => {
    if (locale !== "ko" && !translated && !translating) {
      void autoTranslate();
    }
  }, [locale]);

  async function autoTranslate() {
    setTranslating(true);
    try {
      const titleRes = await fetchApi<{ translated_text: string }>("/community/translate", {
        method: "POST",
        body: JSON.stringify({ target_type: "post", target_id: post.id, target_language: locale }),
      });
      setTranslated({ title: titleRes.translated_text, content: undefined });
    } catch {
      // 번역 실패 시 원문 유지
    } finally {
      setTranslating(false);
    }
  }

  const displayTitle = translated?.title || post.title;
  const displayContent = translated?.content || post.content;

  return (
    <Pressable onPress={onPress}>
      <Card style={styles.post}>
        <View style={styles.postTop}>
          <View style={styles.authorRow}>
            <View style={styles.avatar}>
              <MaterialIcons name="person" size={18} color={stitch.blue} />
            </View>
            <View>
              <Text style={styles.author}>{post.anonymous_name || "익명"}</Text>
              <Text style={styles.time}>{post.created_at?.slice(0, 10) || ""}</Text>
            </View>
          </View>
          <Text style={styles.category}>{t("community.categories." + post.category) || post.category}</Text>
        </View>

        <Text style={styles.postTitle}>{displayTitle}</Text>
        <Text style={styles.postBody} numberOfLines={3}>{displayContent}</Text>

        {locale === "ko" && !translated ? (
          <Pressable style={styles.translateButton} onPress={autoTranslate} disabled={translating}>
            <MaterialIcons name="translate" size={16} color={stitch.blue} />
            <Text style={styles.translateText}>{t("community.translate")}</Text>
          </Pressable>
        ) : translating ? (
          <View style={styles.translateButton}>
            <ActivityIndicator size="small" color={stitch.blue} />
            <Text style={styles.translateText}>{t("common.loading")}</Text>
          </View>
        ) : null}

        <RemoteImage uri={image} style={styles.feedImage} />

        <View style={styles.actionRow}>
          <View style={styles.leftActions}>
            <Action icon={post.my_liked ? "favorite" : "favorite-border"} label={String(post.like_count || 0)} active={post.my_liked} />
            <Action icon="chat-bubble-outline" label={String(post.comment_count || 0)} />
          </View>
          <MaterialIcons name="bookmark-border" size={22} color={stitch.outline} />
        </View>
      </Card>
    </Pressable>
  );
}

function Action({
  icon,
  label,
  active,
}: {
  icon: keyof typeof MaterialIcons.glyphMap;
  label: string;
  active?: boolean;
}) {
  return (
    <View style={styles.action}>
      <MaterialIcons name={icon} size={21} color={active ? stitch.blue : stitch.muted} />
      <Text style={[styles.actionText, active && { color: stitch.blue }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: 132 },
  stickyArea: { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 10, gap: 14, backgroundColor: stitch.bg },
  searchBox: { height: 48, borderRadius: 12, backgroundColor: stitch.surfaceLow, borderWidth: 1, borderColor: "rgba(198,198,205,0.65)", paddingHorizontal: 12, flexDirection: "row", alignItems: "center", gap: 10 },
  searchInput: { flex: 1, color: stitch.text, fontSize: 15, fontWeight: "700" },
  tuneButton: { width: 34, height: 34, borderRadius: 17, backgroundColor: stitch.surface, alignItems: "center", justifyContent: "center" },
  filters: { gap: 8, paddingRight: 20 },
  feed: { paddingHorizontal: 20, paddingTop: 10, gap: 16 },
  post: { overflow: "hidden" },
  postTop: { padding: 16, paddingBottom: 8, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  authorRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  avatar: { width: 34, height: 34, borderRadius: 17, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  author: { color: stitch.text, fontSize: 13, fontWeight: "900" },
  time: { marginTop: 2, color: stitch.outline, fontSize: 11, fontWeight: "700" },
  category: { color: stitch.green, backgroundColor: "rgba(0,150,104,0.1)", borderRadius: 5, overflow: "hidden", paddingHorizontal: 8, paddingVertical: 4, fontSize: 11, fontWeight: "900" },
  postTitle: { paddingHorizontal: 16, color: stitch.text, fontSize: 20, lineHeight: 28, fontWeight: "900" },
  postBody: { paddingHorizontal: 16, marginTop: 8, color: stitch.muted, fontSize: 14, lineHeight: 21, fontWeight: "600" },
  translateButton: { paddingHorizontal: 16, marginTop: 12, marginBottom: 12, flexDirection: "row", alignItems: "center", gap: 5 },
  translateText: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  feedImage: { height: 190, borderRadius: 10, marginHorizontal: 16 },
  actionRow: { marginTop: 12, borderTopWidth: 1, borderTopColor: "rgba(198,198,205,0.25)", padding: 14, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  leftActions: { flexDirection: "row", gap: 24 },
  action: { flexDirection: "row", alignItems: "center", gap: 5 },
  actionText: { color: stitch.muted, fontSize: 12, fontWeight: "900" },
  empty: { padding: 28, alignItems: "center", gap: 8 },
  emptyTitle: { color: stitch.text, fontSize: 18, fontWeight: "900" },
  emptyBody: { color: stitch.muted, fontSize: 13, fontWeight: "700" },
  fab: { position: "absolute", right: 20, bottom: 94, minHeight: 52, borderRadius: 26, paddingHorizontal: 18, backgroundColor: stitch.navy, flexDirection: "row", alignItems: "center", gap: 8, shadowColor: "#0f172a", shadowOpacity: 0.22, shadowRadius: 12, shadowOffset: { width: 0, height: 8 }, elevation: 8 },
  fabText: { color: "#fff", fontSize: 15, fontWeight: "900" },
});
