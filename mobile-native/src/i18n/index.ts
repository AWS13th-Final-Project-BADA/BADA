import { I18n } from "i18n-js";
import ko from "./messages/ko.json";
import vi from "./messages/vi.json";
import en from "./messages/en.json";

export const SUPPORTED = ["ko", "vi", "en"] as const;
export type Locale = (typeof SUPPORTED)[number];
export const DEFAULT_LOCALE: Locale = "ko";

export const i18n = new I18n({ ko, vi, en });

i18n.enableFallback = true;
i18n.defaultLocale = DEFAULT_LOCALE;
i18n.locale = DEFAULT_LOCALE;

export function setLocale(locale: Locale) {
  i18n.locale = locale;
}

export function t(key: string, options?: Record<string, unknown>) {
  return i18n.t(key, options);
}
