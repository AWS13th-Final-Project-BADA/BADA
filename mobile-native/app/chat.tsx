import { useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
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
import type { ChatResponse, ChatSource } from "@/lib/types";
import { Card, StitchScreen, TopBar, stitch } from "@/components/StitchKit";

interface Msg {
  role: "user" | "ai";
  text: string;
  actions?: string[];
  sources?: ChatSource[];
}

const suggested = [
  "이 패키지에서 중요한 내용이 뭐예요?",
  "상담하러 가면 뭐부터 말하면 좋을까요?",
  "진정서에는 어떤 내용을 적어야 해요?",
];

export default function ChatScreen() {
  const { caseId } = useLocalSearchParams<{ caseId?: string }>();
  const activeCaseId = typeof caseId === "string" && caseId.trim() ? caseId : null;
  const scrollRef = useRef<ScrollView>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [selectedSource, setSelectedSource] = useState<ChatSource | null>(null);
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "ai",
      text:
        "안녕하세요. 업로드한 자료를 기준으로 상담 전에 정리할 쟁점과 질문을 도와드릴게요. BADA는 법률 판단이 아니라 상담 준비 안내를 제공합니다.",
    },
  ]);

  async function send(textOverride?: string) {
    const text = (textOverride ?? input).trim();
    if (!text || busy) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setBusy(true);

    try {
      const res = await fetchApi<ChatResponse>("/chat/messages", {
        method: "POST",
        body: JSON.stringify({
          case_id: activeCaseId,
          message: text,
          language: "auto",
        }),
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: res.answer,
          actions: res.next_actions,
          sources: res.sources,
        },
      ]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: `지금은 답변을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.\n(${String(e?.message ?? e)})`,
        },
      ]);
    } finally {
      setBusy(false);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
    }
  }

  return (
    <StitchScreen scroll={false} bottom={false} active="assistant">
      <KeyboardAvoidingView
        style={styles.wrap}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={16}
      >
        <TopBar title="BADA AI" back right="info-outline" />

        <View style={styles.contextBar}>
          <View style={styles.liveDot} />
          <Text style={styles.contextText}>
            {activeCaseId ? `현재 사건: ${activeCaseId.slice(0, 8)}` : "사건을 선택하면 자료 기반 답변이 더 정확해져요"}
          </Text>
          <MaterialIcons name="description" size={18} color={stitch.outline} />
        </View>

        <ScrollView
          ref={scrollRef}
          style={styles.thread}
          contentContainerStyle={styles.threadContent}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((message, index) => (
            <Bubble key={`${message.role}-${index}`} message={message} onSourcePress={setSelectedSource} />
          ))}

          {busy ? (
            <View style={styles.aiRow}>
              <View style={styles.aiAvatar}>
                <MaterialIcons name="smart-toy" size={18} color="#fff" />
              </View>
              <View style={styles.loadingBubble}>
                <ActivityIndicator color={stitch.blue} />
              </View>
            </View>
          ) : null}

          <View style={styles.suggestedBlock}>
            <Text style={styles.suggestedLabel}>추천 질문</Text>
            <View style={styles.suggestedList}>
              {suggested.map((item) => (
                <Pressable key={item} style={styles.suggestedChip} onPress={() => send(item)}>
                  <Text style={styles.suggestedText}>{item}</Text>
                  <MaterialIcons name="chevron-right" size={18} color={stitch.blue} />
                </Pressable>
              ))}
            </View>
          </View>
        </ScrollView>

        <View style={styles.inputPanel}>
          <Card style={styles.inputCard}>
            <TextInput
              value={input}
              onChangeText={setInput}
              placeholder="상담 준비에 대해 물어보세요"
              placeholderTextColor={stitch.outline}
              style={styles.input}
              multiline
            />
            <Pressable style={[styles.send, busy && { opacity: 0.5 }]} onPress={() => send()} disabled={busy}>
              <MaterialIcons name="send" size={20} color="#fff" />
            </Pressable>
          </Card>
          <View style={styles.guardrail}>
            <MaterialIcons name="verified-user" size={16} color={stitch.outline} />
            <Text style={styles.guardrailText}>법률 판단 대신 상담 준비와 자료 정리를 도와드려요</Text>
          </View>
        </View>
      </KeyboardAvoidingView>
      <SourceDetailModal source={selectedSource} onClose={() => setSelectedSource(null)} />
    </StitchScreen>
  );
}

function Bubble({ message, onSourcePress }: { message: Msg; onSourcePress: (source: ChatSource) => void }) {
  if (message.role === "user") {
    return (
      <View style={styles.userRow}>
        <View style={styles.userAvatar}>
          <MaterialIcons name="person" size={18} color="#fff" />
        </View>
        <View style={styles.userBubble}>
          <Text style={styles.userText}>{message.text}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.aiRow}>
      <View style={styles.aiAvatar}>
        <MaterialIcons name="smart-toy" size={18} color="#fff" />
      </View>
      <View style={{ flex: 1, gap: 8 }}>
        <View style={styles.aiBubble}>
          <Text style={styles.aiText}>{message.text}</Text>
          {message.actions?.length ? (
            <View style={styles.actionList}>
              {message.actions.slice(0, 3).map((action) => (
                <Text key={action} style={styles.actionItem}>- {action}</Text>
              ))}
            </View>
          ) : null}
        </View>
        {message.sources?.length ? (
          <View style={styles.sourceRow}>
            {message.sources.map((source, index) => (
              <Pressable
                key={`${source.source_id}-${source.section ?? index}`}
                style={({ pressed }) => [styles.sourceChip, pressed && styles.sourceChipPressed]}
                onPress={() => onSourcePress(source)}
                accessibilityRole="button"
                accessibilityLabel={`${source.title} 참고 자료 보기`}
              >
                <MaterialIcons name="description" size={14} color={stitch.blue} />
                <Text style={styles.sourceText} numberOfLines={1}>{source.title}</Text>
                <MaterialIcons name="chevron-right" size={14} color={stitch.outline} />
              </Pressable>
            ))}
          </View>
        ) : null}
      </View>
    </View>
  );
}

function SourceDetailModal({ source, onClose }: { source: ChatSource | null; onClose: () => void }) {
  if (!source) return null;

  return (
    <Modal transparent visible animationType="slide" statusBarTranslucent onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="참고 자료 닫기" />
        <View style={styles.sourceSheet}>
          <View style={styles.sheetHandle} />
          <View style={styles.sheetHeader}>
            <View style={styles.sheetIcon}>
              <MaterialIcons name="verified" size={20} color={stitch.blue} />
            </View>
            <View style={styles.sheetHeading}>
              <Text style={styles.sheetEyebrow}>참고한 자료</Text>
              <Text style={styles.sheetTitle}>{source.title}</Text>
            </View>
            <Pressable style={styles.closeButton} onPress={onClose} accessibilityRole="button" accessibilityLabel="닫기">
              <MaterialIcons name="close" size={22} color={stitch.muted} />
            </Pressable>
          </View>

          <View style={styles.sourceMeta}>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>제공 기관</Text>
              <Text style={styles.metaValue}>{source.source_org}</Text>
            </View>
            {source.section ? (
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>관련 항목</Text>
                <Text style={styles.metaValue}>{source.section}</Text>
              </View>
            ) : null}
          </View>

          <View style={styles.excerptBlock}>
            <Text style={styles.excerptLabel}>질문과 관련된 내용</Text>
            <Text style={styles.excerptText}>
              {source.excerpt || "이 답변을 준비할 때 관련 항목을 참고했습니다."}
            </Text>
          </View>

          <View style={styles.sourceNotice}>
            <MaterialIcons name="info-outline" size={16} color={stitch.outline} />
            <Text style={styles.sourceNoticeText}>답변은 이 자료의 관련 내용을 참고해 생성했어요.</Text>
          </View>
        </View>
      </View>
    </Modal>
  );
}
const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: stitch.bg },
  contextBar: {
    minHeight: 42,
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: stitch.surface,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(198,198,205,0.35)",
  },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: stitch.green },
  contextText: { flex: 1, color: stitch.muted, fontSize: 12, fontWeight: "800" },
  thread: { flex: 1 },
  threadContent: { padding: 20, paddingBottom: 180, gap: 18 },
  aiRow: { flexDirection: "row", alignItems: "flex-start", gap: 12, maxWidth: "92%" },
  aiAvatar: { width: 34, height: 34, borderRadius: 17, backgroundColor: "#131b2e", alignItems: "center", justifyContent: "center" },
  aiBubble: { backgroundColor: stitch.surface, borderWidth: 1, borderColor: "rgba(198,198,205,0.5)", borderTopRightRadius: 16, borderBottomLeftRadius: 16, borderBottomRightRadius: 16, padding: 14, gap: 10 },
  aiText: { color: stitch.text, fontSize: 14, lineHeight: 22, fontWeight: "600" },
  loadingBubble: { minWidth: 68, height: 48, borderRadius: 14, backgroundColor: stitch.surface, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "rgba(198,198,205,0.5)" },
  userRow: { flexDirection: "row-reverse", alignItems: "flex-start", gap: 12, alignSelf: "flex-end", maxWidth: "88%" },
  userAvatar: { width: 34, height: 34, borderRadius: 17, backgroundColor: stitch.navy, alignItems: "center", justifyContent: "center" },
  userBubble: { backgroundColor: stitch.blueStrong, borderTopLeftRadius: 16, borderBottomLeftRadius: 16, borderBottomRightRadius: 16, padding: 14 },
  userText: { color: "#fff", fontSize: 14, lineHeight: 22, fontWeight: "700" },
  actionList: { borderTopWidth: 1, borderTopColor: "rgba(198,198,205,0.45)", paddingTop: 8, gap: 4 },
  actionItem: { color: stitch.muted, fontSize: 12, lineHeight: 18, fontWeight: "700" },
  sourceRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  sourceChip: { flexDirection: "row", alignItems: "center", gap: 5, backgroundColor: stitch.surfaceLow, borderRadius: 6, borderWidth: 1, borderColor: "rgba(49,107,243,0.2)", paddingHorizontal: 8, paddingVertical: 6, maxWidth: "100%" },
  sourceChipPressed: { opacity: 0.7, backgroundColor: stitch.blueSoft },
  sourceText: { flexShrink: 1, color: stitch.muted, fontSize: 11, fontWeight: "800" },
  suggestedBlock: { gap: 10, paddingTop: 6 },
  suggestedLabel: { color: stitch.outline, fontSize: 12, fontWeight: "900" },
  suggestedList: { gap: 8 },
  suggestedChip: { minHeight: 48, borderRadius: 12, backgroundColor: stitch.surface, borderWidth: 1, borderColor: "rgba(198,198,205,0.6)", paddingHorizontal: 14, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  suggestedText: { flex: 1, color: stitch.text, fontSize: 13, lineHeight: 19, fontWeight: "700" },
  inputPanel: { position: "absolute", left: 0, right: 0, bottom: 0, padding: 16, paddingBottom: 20, backgroundColor: "rgba(247,249,251,0.94)", borderTopWidth: 1, borderTopColor: "rgba(198,198,205,0.35)" },
  inputCard: { minHeight: 58, paddingHorizontal: 12, paddingVertical: 8, flexDirection: "row", alignItems: "flex-end", gap: 10 },
  input: { flex: 1, minHeight: 40, maxHeight: 100, color: stitch.text, fontSize: 15, lineHeight: 21, fontWeight: "600" },
  send: { width: 42, height: 42, borderRadius: 21, backgroundColor: stitch.navy, alignItems: "center", justifyContent: "center" },
  guardrail: { marginTop: 8, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
  guardrailText: { color: stitch.outline, fontSize: 11, fontWeight: "700" },
  modalOverlay: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(15,23,42,0.42)" },
  sourceSheet: { width: "100%", maxWidth: 560, maxHeight: "76%", alignSelf: "center", backgroundColor: stitch.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, paddingHorizontal: 20, paddingTop: 10, paddingBottom: 28, gap: 18 },
  sheetHandle: { width: 38, height: 4, borderRadius: 2, backgroundColor: stitch.line, alignSelf: "center" },
  sheetHeader: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  sheetIcon: { width: 40, height: 40, borderRadius: 12, backgroundColor: stitch.blueSoft, alignItems: "center", justifyContent: "center" },
  sheetHeading: { flex: 1, gap: 4 },
  sheetEyebrow: { color: stitch.blue, fontSize: 12, fontWeight: "900" },
  sheetTitle: { color: stitch.text, fontSize: 18, lineHeight: 25, fontWeight: "900" },
  closeButton: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: stitch.surfaceLow },
  sourceMeta: { gap: 10, paddingVertical: 14, borderTopWidth: 1, borderBottomWidth: 1, borderColor: "rgba(198,198,205,0.42)" },
  metaRow: { flexDirection: "row", alignItems: "flex-start", gap: 14 },
  metaLabel: { width: 66, color: stitch.outline, fontSize: 12, lineHeight: 18, fontWeight: "800" },
  metaValue: { flex: 1, color: stitch.text, fontSize: 13, lineHeight: 19, fontWeight: "700" },
  excerptBlock: { gap: 8 },
  excerptLabel: { color: stitch.text, fontSize: 14, fontWeight: "900" },
  excerptText: { color: stitch.muted, fontSize: 14, lineHeight: 22, fontWeight: "600" },
  sourceNotice: { flexDirection: "row", alignItems: "center", gap: 7, padding: 12, borderRadius: 8, backgroundColor: stitch.surfaceLow },
  sourceNoticeText: { flex: 1, color: stitch.outline, fontSize: 11, lineHeight: 16, fontWeight: "700" },
});
