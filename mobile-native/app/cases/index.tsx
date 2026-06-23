import { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  RefreshControl,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { fetchApi, ApiError } from "@/lib/api";
import { t } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

interface Case {
  id: string;
  title: string;
  workplace_name: string | null;
  status: string;
  created_at: string;
}

export default function CasesList() {
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await fetchApi<Case[]>("/cases");
      setCases(Array.isArray(data) ? data : []);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/login");
        return;
      }
      setError("목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <FlatList
      style={styles.list}
      contentContainerStyle={{ padding: spacing.md, gap: spacing.sm }}
      data={cases}
      keyExtractor={(c) => c.id}
      refreshControl={
        <RefreshControl refreshing={false} onRefresh={load} />
      }
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={styles.h1}>{t("cases.title")}</Text>
          <Pressable
            style={styles.createBtn}
            onPress={() => router.push("/cases/new")}
          >
            <Text style={styles.createText}>+ {t("cases.create")}</Text>
          </Pressable>
        </View>
      }
      renderItem={({ item }) => (
        <Pressable
          style={styles.card}
          onPress={() => router.push(`/cases/${item.id}`)}
        >
          <View style={{ flex: 1 }}>
            <Text style={styles.cardTitle}>
              {item.workplace_name || item.title}
            </Text>
            <Text style={styles.cardDate}>
              {item.created_at?.slice(0, 10)}
            </Text>
          </View>
          <Text style={styles.badge}>{item.status}</Text>
        </Pressable>
      )}
      ListEmptyComponent={
        <Text style={styles.empty}>
          {error ?? "아직 사건이 없습니다."}
        </Text>
      }
    />
  );
}

const styles = StyleSheet.create({
  list: { flex: 1 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  h1: { fontSize: 20, fontWeight: "700", color: colors.text },
  createBtn: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.sm,
  },
  createText: { color: "#fff", fontWeight: "600", fontSize: 13 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  cardTitle: { fontWeight: "600", fontSize: 15, color: colors.text },
  cardDate: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  badge: {
    backgroundColor: colors.badge,
    color: colors.textMuted,
    fontSize: 11,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.full,
    overflow: "hidden",
  },
  empty: {
    textAlign: "center",
    color: colors.textMuted,
    paddingVertical: spacing.xl * 2,
  },
});
