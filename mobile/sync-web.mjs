// 웹 프론트(backend/app/static)를 Capacitor webDir(www)로 복사 + 백엔드 주소 주입.
// 실행: npm run build  (또는 node sync-web.mjs)
import { rmSync, mkdirSync, cpSync, renameSync, copyFileSync, writeFileSync, readFileSync, existsSync } from "fs";
import { join } from "path";

const SRC = join("..", "backend", "app", "static");
const WWW = "www";

if (!existsSync(SRC)) {
  console.error("backend/app/static 를 찾을 수 없습니다. mobile/ 폴더에서 실행하세요.");
  process.exit(1);
}

// 1) www 초기화
rmSync(WWW, { recursive: true, force: true });
mkdirSync(join(WWW, "static"), { recursive: true });

// 2) static/* → www/static/*
cpSync(SRC, join(WWW, "static"), { recursive: true });

// 3) index.html 은 www 루트로 (앱 진입점)
renameSync(join(WWW, "static", "index.html"), join(WWW, "index.html"));

// 4) 루트 경로로 참조되는 manifest·sw 도 루트에 복사 (없어도 무해)
for (const f of ["manifest.webmanifest", "sw.js"]) {
  const from = join(WWW, "static", f);
  if (existsSync(from)) copyFileSync(from, join(WWW, f));
}

// 5) 백엔드 주소 주입 — config.js 의 BADA_API 기본값만 교체.
//    (상태바·뒤로가기 핸들러 등 config.js 의 나머지 내용은 그대로 유지)
const cfgPath = join(WWW, "static", "js", "config.js");
const apiBase = JSON.parse(readFileSync("app-config.json", "utf8")).apiBase || "";
let cfgJs = readFileSync(cfgPath, "utf8");
const before = cfgJs;
cfgJs = cfgJs.replace(/window\.BADA_API\s*=\s*window\.BADA_API\s*\|\|\s*"";/,
                      `window.BADA_API = ${JSON.stringify(apiBase)};`);
if (cfgJs === before) {
  // 패턴 못 찾으면 안전하게 맨 앞에 주입
  cfgJs = `window.BADA_API = ${JSON.stringify(apiBase)};\n` + cfgJs;
}
writeFileSync(cfgPath, cfgJs);

console.log(`✓ www/ 생성 완료 — apiBase = ${apiBase || "(빈값: 같은 출처)"}`);
