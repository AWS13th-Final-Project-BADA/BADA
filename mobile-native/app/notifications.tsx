import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { fetchApi } from "@/lib/api";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";
import { Card, StitchScreen, TopBar, stitch } from "@/components/StitchKit";

interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string | null;
  case_id: string | null;
  is_read: boolean;
  created_at: string | null;
}

export default function NotificationsScreen() {
  const router = useRouter();
  const { locale } = useLocale();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      fetchApi<NotificationItem[]>("/notifications")
        .then(setItems)
        .catch(() => setItems([]))
        .finally(() => setLoading(false));
    }, [])
  );

  async function markRead(id: string) {
    await fetchApi(`/notifications/${id}/read`, { method: "PATCH" }).catch(() => {});
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
  }

  async function markAllRead() {
    await fetchApi("/notifications/read-all", { method: "PATCH" }).catch(() => {});
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
  }

  function getIcon(type: string): keyof typeof MaterialIcons.glyphMap {
    if (type === "analysis_complete") return "analytics";
    if (type === "comment") return "chat-bubble";
    return "notifications";
  }

  function getColor(type: string): string {
    if (type === "analysis_complete") return stitch.blue;
    if (type === "comment") return stitch.amber;
    return stitch.outline;
  }

  return (
    <StitchScreen>
      <TopBar title={t("nav.notifications")} back />
      <View style={styles.content}>
        {items.filter((n) => !n.is_read).length > 0 && (
          <Pressable style={styles.readAll} onPress={markAllRead}>
            <Text style={styles.readAllText}>{t("common.confirm")}</Text>
          </Pressable>
        )}

        {loading && <ActivityIndicator color={stitch.blue} style={{ marginTop: 40 }} />}

        {!loading && items.length === 0 && (
          <View style={styles.empty}>
            <MaterialIcons name="notifications-none" size={48} color={stitch.outline} />
            <Text style={styles.emptyText}>{t("nav.noNotifications")}</Text>
          </View>
        )}

        {items.map((item) => (
          <Pressable
            key={item.id}
            style={[styles.item, !item.is_read && styles.itemUnread]}
            onPress={() => {
              markRead(item.id);
              if (item.case_id) router.push({ pathname: "/cases/[id]", params: { id: item.case_id } });
            }}
          >
            <View style={[styles.iconWrap, { backgroundColor: `${getColor(item.type)}1A` }]}>
              <MaterialIcons name={getIcon(item.type)} size={22} color={getColor(item.type)} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.title}>{item.title}</Text>
              {item.body && <Text style={styles.body}>{item.body}</Text>}
              {item.created_at && <Text style={styles.time}>{item.created_at.slice(0, 10)}</Text>}
            </View>
            {!item.is_read && <View style={styles.dot} />}
          </Pressable>
        ))}
      </View>
    </StitchScreen>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 10 },
  readAll: { alignSelf: "flex-end", paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6, backgroundColor: stitch.blueSoft },
  readAllText: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  empty: { alignItems: "center", paddingTop: 80, gap: 12 },
  emptyText: { color: stitch.muted, fontSize: 14, fontWeight: "700" },
  item: { flexDirection: "row", alignItems: "center", gap: 14, padding: 14, borderRadius: 12, backgroundColor: stitch.surface, borderWidth: 1, borderColor: "rgba(198,198,205,0.3)" },
  itemUnread: { backgroundColor: "rgba(0,81,213,0.04)", borderColor: "rgba(0,81,213,0.15)" },
  iconWrap: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  title: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  body: { color: stitch.muted, fontSize: 12, fontWeight: "700", marginTop: 2 },
  time: { color: stitch.outline, fontSize: 11, fontWeight: "700", marginTop: 4 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: stitch.blue },
});
