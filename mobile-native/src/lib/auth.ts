/**
 * Cognito / 소셜 로그인 — 네이티브 흐름.
 *
 * web은 `/auth/cognito/login` → Cognito → 백엔드 콜백 → `#token=...` 해시로 웹에 반환.
 * 네이티브는 시스템 브라우저 세션을 열고 앱 스킴 딥링크(`bada://auth?token=...`)로
 * 토큰을 돌려받는다.
 *
 * ⚠️ 백엔드 연계 필요(계획서 §6):
 *   콜백이 `redirect_uri=bada://auth`(또는 `app=1`)를 받으면 웹 해시 대신
 *   앱 스킴으로 302 리다이렉트하도록 한 분기 추가가 필요하다.
 *   합의 전까지는 setTokenManually()로 데모 토큰 주입을 지원한다.
 */
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { API_BASE, setToken, clearToken } from "./api";

WebBrowser.maybeCompleteAuthSession();

const APP_REDIRECT = Linking.createURL("auth"); // exp://… 또는 bada://auth

type Provider = "cognito" | "kakao" | "google" | "naver";

function extractToken(url: string): string | null {
  // 지원: bada://auth?token=... / bada://auth#token=...
  const q = url.split(/[?#]/)[1];
  if (!q) return null;
  for (const part of q.split("&")) {
    const [k, v] = part.split("=");
    if (k === "token" && v) return decodeURIComponent(v);
  }
  return null;
}

export async function login(provider: Provider = "cognito"): Promise<boolean> {
  const loginPath =
    provider === "cognito" ? "/auth/cognito/login" : `/auth/${provider}/login`;
  const authUrl = `${API_BASE}${loginPath}?redirect_uri=${encodeURIComponent(
    APP_REDIRECT
  )}`;

  const result = await WebBrowser.openAuthSessionAsync(authUrl, APP_REDIRECT);
  if (result.type === "success" && result.url) {
    const token = extractToken(result.url);
    if (token) {
      await setToken(token);
      return true;
    }
  }
  return false;
}

export async function logout(): Promise<void> {
  await clearToken();
  // 백엔드 Cognito 로그아웃(세션 종료)은 선택 — 브라우저로 호출 가능.
  WebBrowser.openBrowserAsync(`${API_BASE}/auth/cognito/logout`).catch(() => {});
}

/** 데모/개발용 토큰 수동 주입 (백엔드 딥링크 연계 전 임시). */
export async function setTokenManually(token: string): Promise<void> {
  await setToken(token);
}

export { APP_REDIRECT };
