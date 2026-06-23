import { useState, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  Pressable,
  ScrollView,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import { fetchApi } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";
import { t, i18n } from "@/i18n";
import { colors, spacing, radius } from "@/theme";

interface Msg {
  role: "user" | "ai";
  text: string;
  actions?: string[];
}

export default function ChatScreen() {
  // 사건 맥락에서 진입하면 caseId 전달(선택).
  // ⚠️ 백엔드 ChatMessageRequest.case_id 는 int 계약인데 사건 id는 UUID라 어긋남.
  //    숫자면 그대로, 아니면 0(일반 상담)으로 보냄 — 계약 정합화는 백엔드 연계 항목.
  const { caseId } = useLocalSearchParams<{ caseId?: string }>();
  const numericCaseId = caseId && /^\d+$/.test(caseId) ? Number(caseId) : 0;

  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "ai",
      text:
        "안녕하세요. BADA 상담 도우미예요. 임금·근무·신고 준비에 대해 모국어로 물어보세요.\n(본 답변은 법률자문이 아닙니다.)",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const res = await fetchApi<ChatResponse>("/chat/messages", {
        method: "POST",
        body: JSON.stringify({
          case_id: numericCaseId,
          message: text,
          language: i18n.locale,
        }),
      });
      setMessages((m) => [
        ...m,
        { role: "ai", text: res.answer, actions: res.next_actions },
      ]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        {
          role: "ai",
          text:
            "지금은 답변을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.\n(" +
            String(e?.message ?? e) +
            ")",
        },
      ]);
    } finally {
      setBusy(false);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.wrap}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView
        ref={scrollRef}
        contentContainerStyle={styles.list}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((m, i) => (
          <View
            key={i}
            style={[styles.bubble, m.role === "user" ? styles.user : styles.ai]}
          >
            <Text style={[styles.bubbleText, m.role === "user" && { color: "#fff" }]}>
              {m.text}
            </Text>
            {m.actions && m.actions.length > 0 && (
              <View style={styles.actions}>
                {m.actions.map((a, j) => (
                  <Text key={j} style={styles.action}>
                    • {a}
                  </Text>
                ))}
              </View>
            )}
          </View>
        ))}
        {busy && (
          <View style={[styles.bubble, styles.ai]}>
            <ActivityIndicator color={colors.primary} />
          </View>
        )}
      </ScrollView>

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="메시지를 입력하세요"
          multiline
        />
        <Pressable style={styles.send} onPress={send} disabled={busy}>
          <Text style={styles.sendText}>전송</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: colors.bg },
  list: { padding: spacing.md, gap: spacing.sm },
  bubble: {
    maxWidth: "85%",
    borderRadius: radius.md,
    padding: spacing.md,
  },
  user: { alignSelf: "flex-end", backgroundColor: colors.primary },
  ai: {
    alignSelf: "flex-start",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  bubbleText: { fontSize: 15, color: colors.text, lineHeight: 21 },
  actions: { marginTop: spacing.sm, gap: 2 },
  action: { fontSize: 13, color: colors.primary },
  inputRow: {
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.card,
    alignItems: "flex-end",
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.sm,
    backgroundColor: "#fff",
    maxHeight: 100,
  },
  send: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    justifyContent: "center",
    height: 40,
  },
  sendText: { color: "#fff", fontWeight: "700" },
});
