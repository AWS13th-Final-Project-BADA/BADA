/**
 * Cognito 인증 유틸리티.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.badasoft.com";

export function loginWithCognito() {
  window.location.href = `${API_BASE}/auth/cognito/login`;
}

export function loginWithProvider(provider: "kakao" | "google" | "naver") {
  window.location.href = `${API_BASE}/auth/${provider}/login`;
}

export function logout() {
  localStorage.removeItem("access_token");
  window.location.href = `${API_BASE}/auth/cognito/logout`;
}

/** 콜백에서 URL hash의 token을 추출하여 저장. */
export function handleAuthCallback(): boolean {
  if (typeof window === "undefined") return false;
  const hash = window.location.hash;
  if (hash.startsWith("#token=")) {
    const token = hash.slice(7);
    localStorage.setItem("access_token", token);
    window.location.hash = "";
    return true;
  }
  return false;
}

export function isLoggedIn(): boolean {
  return typeof window !== "undefined" && !!localStorage.getItem("access_token");
}
