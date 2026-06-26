import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { i18n, setLocale as setI18nLocale, SUPPORTED, DEFAULT_LOCALE } from "./index";
import type { Locale } from "./index";

const LOCALE_KEY = "bada_locale";

interface LocaleContextValue {
  locale: Locale;
  changeLocale: (lang: Locale) => void;
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: DEFAULT_LOCALE,
  changeLocale: () => {},
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(i18n.locale as Locale);

  useEffect(() => {
    AsyncStorage.getItem(LOCALE_KEY).then((saved) => {
      if (saved && SUPPORTED.includes(saved as Locale)) {
        setI18nLocale(saved as Locale);
        setLocale(saved as Locale);
      }
    });
  }, []);

  const changeLocale = useCallback((lang: Locale) => {
    setI18nLocale(lang);
    setLocale(lang);
    AsyncStorage.setItem(LOCALE_KEY, lang);
  }, []);

  return (
    <LocaleContext.Provider value={{ locale, changeLocale }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  return useContext(LocaleContext);
}
