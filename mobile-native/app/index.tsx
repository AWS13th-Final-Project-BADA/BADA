import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import { ApiError, fetchApi, isLoggedIn } from "@/lib/api";
import { logout } from "@/lib/auth";
import { stitchImages } from "@/lib/stitchAssets";
import { Card, RemoteImage, SectionLabel, StitchButton, StitchScreen, TopBar, stitch } from "@/components/StitchKit";
import { t } from "@/i18n";
import { useLocale } from "@/i18n/LocaleContext";
import type { CommunityPost } from "@/lib/types";

interface CurrentUser {
  id: string;
  email: string | null;
  name: string | null;
  preferred_lang?: string | null;
  provider?: string | null;
}

export default function Home() {
  const router = useRouter();
  const { locale } = useLocale(); // locale 변경 시 리렌더 트리거
  const [checking, setChecking] = useState(true);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [recentPosts, setRecentPosts] = useState<CommunityPost[]>([]);

  useEffect(() => {
    let mounted = true;

    async function bootstrap() {
      try {
        const hasToken = await isLoggedIn();
        if (!hasToken) {
          router.replace("/login");
          return;
        }

        const me = await fetchApi<CurrentUser>("/auth/me");
        if (!mounted) return;
        setUser(me);

        // 최근 커뮤니티 글 로드
        try {
          const res = await fetchApi<{ posts: CommunityPost[] }>("/community/posts?limit=3&sort=recent");
          if (mounted) setRecentPosts(res.posts ?? []);
        } catch {
          // 커뮤니티 로드 실패해도 홈 화면은 정상 표시
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        router.replace("/login");
      } finally {
        if (mounted) setChecking(false);
      }
    }

    void bootstrap();
    return () => {
      mounted = false;
    };
  }, [router]);

  if (checking) {
    return (
      <StitchScreen scroll={false} bottom={false}>
        <View style={styles.center}>
          <ActivityIndicator color={stitch.blue} />
          <Text style={styles.loadingText}>{t("common.loading")}</Text>
        </View>
      </StitchScreen>
    );
  }

  if (!user) return null;

  const displayName = user.name || user.email?.split("@")[0] || "사용자";

  async function signOut() {
    await logout();
    router.replace("/login");
  }

  return (
    <StitchScreen active="home">
      <TopBar title="BADA" />
      <View style={styles.content}>
        <View style={styles.greetingRow}>
          <View style={styles.greeting}>
            <Text style={styles.greetingTitle}>{displayName} 님</Text>
            <Text style={styles.greetingBody}>{t("home.dashboardSubtitle")}</Text>
          </View>
          <Pressable style={styles.logoutButton} onPress={signOut}>
            <Text style={styles.logoutText}>{t("common.logout")}</Text>
          </Pressable>
        </View>

        <Card style={styles.currentCard}>
          <View style={styles.currentTop}>
            <View>
              <Text style={styles.badge}>CASE WORKFLOW</Text>
              <Text style={styles.currentTitle}>{t("home.title")}</Text>
            </View>
            <MaterialIcons name="description" size={30} color={stitch.blueStrong} />
          </View>

          <View style={styles.stepWrap}>
            <View style={styles.stepLine} />
            <View style={styles.stepLineOn} />
            <Step done label={t("home.steps.case")} />
            <Step current label={t("home.steps.upload")} value="2" />
            <Step label={t("home.steps.organize")} value="3" />
            <Step label={t("home.steps.consult")} value="4" />
          </View>

          <StitchButton onPress={() => router.push("/cases/new")}>{t("cases.create")}</StitchButton>
        </Card>

        <SectionLabel>{t("home.quickTitle")}</SectionLabel>
        <View style={styles.quickRow}>
          <QuickCard
            icon="folder-open"
            color={stitch.blue}
            bg="rgba(0,81,213,0.1)"
            title={t("cases.myList")}
            body={t("home.quick.caseBody")}
            onPress={() => router.push("/cases")}
          />
          <QuickCard
            icon="smart-toy"
            color={stitch.blue}
            bg={stitch.blueSoft}
            title={t("home.quick.chatAsk")}
            body={t("home.quick.chatBody")}
            onPress={() => router.push("/chat")}
          />
          <QuickCard
            icon="forum"
            color={stitch.amber}
            bg={stitch.amberSoft}
            title={t("home.quick.community")}
            body={t("home.quick.communityBody")}
            onPress={() => router.push("/community")}
          />
        </View>

        <SectionLabel action={<Pressable onPress={() => router.push("/community")}><Text style={styles.viewAll}>{t("home.recentTitle")}</Text></Pressable>}>{t("community.title")}</SectionLabel>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.communityScroll}>
          {recentPosts.length > 0 ? (
            recentPosts.map((post, index) => (
              <Pressable key={post.id} onPress={() => router.push({ pathname: "/community/[id]", params: { id: post.id } })}>
                <CommunityPreview
                  image={index % 2 === 0 ? stitchImages.office : stitchImages.dashboard}
                  category={t("community.categories." + (post.category || "free"))}
                  title={post.title}
                  body={post.content?.slice(0, 60) || ""}
                />
              </Pressable>
            ))
          ) : (
            <Card style={styles.emptyPreview}>
              <Text style={styles.emptyPreviewText}>{t("community.emptyTitle")}</Text>
            </Card>
          )}
        </ScrollView>
      </View>
    </StitchScreen>
  );
}

function Step({
  done,
  current,
  label,
  value,
}: {
  done?: boolean;
  current?: boolean;
  label: string;
  value?: string;
}) {
  return (
    <View style={[styles.step, !done && !current && styles.stepDim]}>
      <View style={[styles.stepDot, done && styles.stepDotOn, current && styles.stepDotCurrent]}>
        {done ? (
          <MaterialIcons name="check" size={17} color="#fff" />
        ) : (
          <Text style={[styles.stepValue, current && styles.stepValueCurrent]}>{value}</Text>
        )}
      </View>
      <Text style={[styles.stepLabel, current && styles.stepLabelCurrent]}>{label}</Text>
    </View>
  );
}

function QuickCard({
  icon,
  color,
  bg,
  title,
  body,
  onPress,
}: {
  icon: keyof typeof MaterialIcons.glyphMap;
  color: string;
  bg: string;
  title: string;
  body: string;
  onPress: () => void;
}) {
  return (
    <Pressable style={styles.quickCard} onPress={onPress}>
      <View style={[styles.quickIcon, { backgroundColor: bg }]}>
        <MaterialIcons name={icon} size={25} color={color} />
      </View>
      <Text style={styles.quickTitle}>{title}</Text>
      <Text style={styles.quickBody}>{body}</Text>
    </Pressable>
  );
}

function CommunityPreview({
  image,
  category,
  title,
  body,
}: {
  image: string;
  category: string;
  title: string;
  body: string;
}) {
  return (
    <Card style={styles.previewCard}>
      <RemoteImage uri={image} style={styles.previewImage} />
      <View style={styles.previewBody}>
        <Text style={styles.previewCategory}>{category}</Text>
        <Text style={styles.previewTitle} numberOfLines={1}>{title}</Text>
        <Text style={styles.previewText} numberOfLines={1}>{body}</Text>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 10 },
  loadingText: { color: stitch.outline, fontSize: 13, fontWeight: "700" },
  content: { padding: 20, gap: 24 },
  greetingRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12 },
  greeting: { flex: 1, marginTop: 2 },
  greetingTitle: { color: stitch.text, fontSize: 22, lineHeight: 30, fontWeight: "900" },
  greetingBody: { marginTop: 4, color: stitch.muted, fontSize: 14, lineHeight: 20, fontWeight: "700" },
  logoutButton: { minHeight: 36, borderRadius: 18, paddingHorizontal: 12, alignItems: "center", justifyContent: "center", backgroundColor: stitch.surfaceLow },
  logoutText: { color: stitch.muted, fontSize: 12, fontWeight: "900" },
  currentCard: { padding: 24, overflow: "hidden" },
  currentTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 26, gap: 16 },
  badge: { alignSelf: "flex-start", backgroundColor: "rgba(0,81,213,0.1)", color: stitch.blue, fontSize: 12, fontWeight: "900", paddingHorizontal: 9, paddingVertical: 5, borderRadius: 4, overflow: "hidden" },
  currentTitle: { marginTop: 10, color: stitch.text, fontSize: 22, lineHeight: 28, fontWeight: "900", maxWidth: 270 },
  stepWrap: { height: 88, flexDirection: "row", justifyContent: "space-between", marginBottom: 18, position: "relative" },
  stepLine: { position: "absolute", left: 0, right: 0, top: 15, height: 2, backgroundColor: "rgba(198,198,205,0.35)" },
  stepLineOn: { position: "absolute", left: 0, width: "34%", top: 15, height: 2, backgroundColor: stitch.blue },
  step: { flex: 1, alignItems: "center", gap: 8 },
  stepDim: { opacity: 0.46 },
  stepDot: { width: 32, height: 32, borderRadius: 16, backgroundColor: stitch.line, alignItems: "center", justifyContent: "center" },
  stepDotOn: { backgroundColor: stitch.blue },
  stepDotCurrent: { backgroundColor: "#fff", borderWidth: 2, borderColor: stitch.blue },
  stepValue: { color: stitch.muted, fontWeight: "900", fontSize: 12 },
  stepValueCurrent: { color: stitch.blue },
  stepLabel: { color: stitch.text, fontSize: 11, lineHeight: 14, fontWeight: "700", textAlign: "center" },
  stepLabelCurrent: { color: stitch.blue, fontWeight: "900" },
  quickGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  quickRow: { flexDirection: "row", gap: 10 },
  quickCard: { flex: 1, minHeight: 120, backgroundColor: stitch.surface, borderRadius: 12, borderWidth: 1, borderColor: "rgba(198,198,205,0.42)", padding: 12, justifyContent: "center", alignItems: "center" },
  quickIcon: { width: 40, height: 40, borderRadius: 8, alignItems: "center", justifyContent: "center", marginBottom: 10 },
  quickTitle: { color: stitch.text, fontSize: 13, lineHeight: 18, fontWeight: "900", textAlign: "center" },
  quickBody: { marginTop: 3, color: stitch.outline, fontSize: 11, lineHeight: 15, fontWeight: "700", textAlign: "center" },
  recommend: { minHeight: 84, backgroundColor: stitch.blueStrong, borderRadius: 12, flexDirection: "row", alignItems: "center", gap: 12, padding: 16 },
  recommendIcon: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: "rgba(255,255,255,0.2)" },
  recommendLabel: { color: "#fff", opacity: 0.9, fontSize: 12, fontWeight: "800" },
  recommendText: { color: "#fff", fontSize: 15, lineHeight: 21, fontWeight: "900" },
  viewAll: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  communityScroll: { paddingHorizontal: 20, gap: 16, paddingBottom: 10 },
  previewCard: { width: 280, overflow: "hidden" },
  previewImage: { height: 128, borderTopLeftRadius: 12, borderTopRightRadius: 12 },
  previewBody: { padding: 16 },
  previewCategory: { color: stitch.blue, fontSize: 12, fontWeight: "800", marginBottom: 6 },
  previewTitle: { color: stitch.text, fontSize: 16, fontWeight: "900" },
  previewText: { marginTop: 6, color: stitch.outline, fontSize: 12, fontWeight: "700" },
  emptyPreview: { width: 280, minHeight: 100, alignItems: "center", justifyContent: "center", padding: 20 },
  emptyPreviewText: { color: stitch.muted, fontSize: 13, fontWeight: "700", textAlign: "center" },
});
