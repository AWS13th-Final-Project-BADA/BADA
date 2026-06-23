/**
 * 다국어(i18n) — 기존 web `frontend/src/messages/*.json`을 그대로 재사용.
 * 지원 언어: ko / vi / en (web routing.ts와 동일).
 */
import { I18n } from "i18n-js";
import { getLocales } from "expo-localization";

import ko from "./messages/ko.json";
import vi from "./messages/vi.json";
import en from "./messages/en.json";

export const SUPPORTED = ["ko", "vi", "en"] as const;
export type Locale = (typeof SUPPORTED)[number];
export const DEFAULT_LOCALE: Locale = "ko";

export const i18n = new I18n({ ko, vi, en });

i18n.enableFallback = true;
i18n.defaultLocale = DEFAULT_LOCALE;

// 단말 언어 자동 감지 → 미지원이면 기본(ko)
const deviceLang = getLocales()[0]?.languageCode ?? DEFAULT_LOCALE;
i18n.locale = (SUPPORTED as readonly string[]).includes(deviceLang)
  ? deviceLang
  : DEFAULT_LOCALE;

export function setLocale(locale: Locale) {
  i18n.locale = locale;
}

/** 짧은 헬퍼: t("cases.title") */
export function t(key: string, options?: Record<string, unknown>) {
  return i18n.t(key, options);
}
