import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["ko", "vi", "en"],
  defaultLocale: "ko",
});
