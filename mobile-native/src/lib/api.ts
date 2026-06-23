/**
 * Backend API 클라이언트 — Bearer 토큰 자동 주입.
 * web `frontend/src/lib/api.ts`의 네이티브 버전.
 * 토큰은 localStorage 대신 expo-secure-store(OS 보안 저장소)에 보관.
 */
import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";

const API_BASE: string =
  (Constants.expoConfig?.extra?.apiBase as string) || "https://api.badasoft.com";

const TOKEN_KEY = "access_token";

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

export async function isLoggedIn(): Promise<boolean> {
  return !!(await getToken());
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function fetchApi<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    await clearToken();
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, `API ${res.status}: ${body}`);
  }
  // 204 등 본문 없는 응답 방어
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

export { API_BASE };
