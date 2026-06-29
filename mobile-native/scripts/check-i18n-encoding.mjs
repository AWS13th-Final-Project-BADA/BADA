import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const messageDir = path.resolve(here, "../src/i18n/messages");
const locales = ["ko", "en", "vi", "ja", "km"];
const scripts = {
  ko: /[\uac00-\ud7a3]/u,
  vi: /[\u00c0-\u024f]/u,
  ja: /[\u3040-\u30ff\u4e00-\u9fff]/u,
  km: /[\u1780-\u17ff]/u,
};
const failures = [];

function inspect(value, key, locale) {
  if (typeof value === "string") {
    if (/\?{2,}|\ufffd/u.test(value)) failures.push(`${locale}:${key}=${JSON.stringify(value)}`);
    return;
  }
  if (value && typeof value === "object") {
    for (const [childKey, childValue] of Object.entries(value)) {
      inspect(childValue, `${key}.${childKey}`, locale);
    }
  }
}

for (const locale of locales) {
  const file = path.join(messageDir, `${locale}.json`);
  let messages;
  try {
    messages = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (error) {
    failures.push(`${locale}: invalid JSON (${error.message})`);
    continue;
  }
  inspect(messages.community, "community", locale);
  if (locale !== "en" && !scripts[locale].test(messages.community?.feedTitle ?? "")) {
    failures.push(`${locale}: community.feedTitle does not contain the expected script`);
  }
}

if (failures.length) {
  console.error("Community i18n encoding check failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Community i18n encoding OK (${locales.length} locales)`);