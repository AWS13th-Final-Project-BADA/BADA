import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import { API_BASE, clearToken, setToken } from "@/lib/api";

WebBrowser.maybeCompleteAuthSession();

const APP_REDIRECT = Linking.createURL("auth");

type Provider = "cognito" | "kakao" | "google" | "naver";

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
  const params = new URLSearchParams({ redirect_uri: APP_REDIRECT });

  if (provider === "google") {
    params.set("identity_provider", "Google");
    params.set("prompt", "select_account");
    return `${API_BASE}/auth/cognito/login?${params.toString()}`;
  }

  if (provider === "cognito") {
    return `${API_BASE}/auth/cognito/login?${params.toString()}`;
  }

  return `${API_BASE}/auth/${provider}/login?${params.toString()}`;
}

export async function login(provider: Provider = "cognito"): Promise<boolean> {
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
  await clearToken();
  const params = new URLSearchParams({ logout_uri: APP_REDIRECT });
  WebBrowser.openBrowserAsync(`${API_BASE}/auth/cognito/logout?${params.toString()}`).catch(() => {});
}


export { APP_REDIRECT };
