import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { i18n, setLocale as setI18nLocale, SUPPORTED, DEFAULT_LOCALE } from "./index";
import type { Locale } from "./index";

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

  const changeLocale = useCallback((lang: Locale) => {
    setI18nLocale(lang);
    setLocale(lang);
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
