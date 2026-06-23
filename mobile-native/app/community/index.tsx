import { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  RefreshControl,
  ActivityIndicator,
} from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { fetchApi, ApiError } from "@/lib/api";
import type { CommunityPost } from "@/lib/types";
import { COMMUNITY_CATEGORY_LABELS } from "@/lib/types";
import { colors, spacing, radius } from "@/theme";

const FILTERS = ["all", "free", "wage", "petition", "review"] as const;

export default function CommunityFeed() {
  const router = useRouter();
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    async (cat = filter) => {
      try {
        const qs = cat === "all" ? "" : `?category=${cat}`;
        const res = await fetchApi<{ posts: CommunityPost[] }>(
          `/community/posts${qs}`
        );
        setPosts(res.posts ?? []);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
      } finally {
        setLoading(false);
      }
    },
    [filter, router]
  );

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  return (
    <View style={styles.wrap}>
      <View style={styles.filters}>
        {FILTERS.map((f) => {
          const on = f === filter;
          return (
            <Pressable
              key={f}
              style={[styles.fchip, on && styles.fchipOn]}
              onPress={() => {
                setFilter(f);
                setLoading(true);
                load(f);
              }}
            >
              <Text style={[styles.fchipText, on && styles.fchipTextOn]}>
                {f === "all" ? "전체" : COMMUNITY_CATEGORY_LABELS[f]}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {loading ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: spacing.xl }} />
      ) : (
        <FlatList
          data={posts}
          keyExtractor={(p) => p.id}
          contentContainerStyle={{ padding: spacing.md, gap: spacing.sm }}
          refreshControl={<RefreshControl refreshing={false} onRefresh={() => load()} />}
          renderItem={({ item }) => (
            <Pressable
              style={styles.card}
              onPress={() =>
                router.push({ pathname: "/community/[id]", params: { id: item.id } })
              }
            >
              <View style={styles.cardHead}>
                <Text style={styles.cat}>
                  {COMMUNITY_CATEGORY_LABELS[item.category] ?? item.category}
                </Text>
                <Text style={styles.date}>{item.created_at?.slice(0, 10)}</Text>
              </View>
              <Text style={styles.cardTitle} numberOfLines={1}>
                {item.title}
              </Text>
              <Text style={styles.cardBody} numberOfLines={2}>
                {item.content}
              </Text>
              <Text style={styles.meta}>
                {item.anonymous_name} · ♡ {item.like_count} · 💬 {item.comment_count}
              </Text>
            </Pressable>
          )}
          ListEmptyComponent={
            <Text style={styles.empty}>아직 게시글이 없습니다.</Text>
          }
        />
      )}

      <Pressable
        style={styles.fab}
        onPress={() => router.push("/community/new")}
      >
        <Text style={styles.fabText}>＋ 글쓰기</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  filters: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xs,
    padding: spacing.sm,
    backgroundColor: colors.card,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  fchip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.full,
    backgroundColor: colors.badge,
  },
  fchipOn: { backgroundColor: colors.primary },
  fchipText: { fontSize: 13, color: colors.textMuted },
  fchipTextOn: { color: "#fff", fontWeight: "600" },
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: 4,
  },
  cardHead: { flexDirection: "row", justifyContent: "space-between" },
  cat: { fontSize: 11, color: colors.primary, fontWeight: "700" },
  date: { fontSize: 11, color: colors.textMuted },
  cardTitle: { fontSize: 15, fontWeight: "700", color: colors.text },
  cardBody: { fontSize: 13, color: colors.textMuted },
  meta: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  empty: { textAlign: "center", color: colors.textMuted, paddingVertical: spacing.xl * 2 },
  fab: {
    position: "absolute",
    right: spacing.lg,
    bottom: spacing.lg,
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.full,
    elevation: 4,
  },
  fabText: { color: "#fff", fontWeight: "700" },
});
