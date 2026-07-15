import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import { API_BASE, clearToken, setToken } from "@/lib/api";

WebBrowser.maybeCompleteAuthSession();

const APP_REDIRECT = Linking.createURL("auth");

type Provider = "google" | "kakao" | "naver";

function extractToken(url: string): string | null {
  const queryParts = url.split(/[?#]/).slice(1);
  for (const query of queryParts) {
    for (const part of query.split("&")) {
      const [k, ...rest] = part.split("=");
      const v = rest.join("=");
      if (k === "token" && v) return decodeURIComponent(v);
    }
  }
  return null;
}

function buildAuthUrl(provider: Provider): string {
  // 소셜 OAuth(구글/카카오/네이버) 직접 구현. 백엔드가 redirect_uri를 state에 보존하고
  // 콜백에서 앱 딥링크(bada://auth#token=)로 302 redirect 한다.
  const params = new URLSearchParams({ redirect_uri: APP_REDIRECT });
  return `${API_BASE}/auth/${provider}/login?${params.toString()}`;
}

export async function login(provider: Provider = "google"): Promise<boolean> {
  const result = await WebBrowser.openAuthSessionAsync(
    buildAuthUrl(provider),
    APP_REDIRECT
  );

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
  // 자체 발급 JWT 기반이라 별도 Hosted UI 로그아웃이 없다. 로컬 토큰만 제거한다.
  await clearToken();
}


export { APP_REDIRECT };
