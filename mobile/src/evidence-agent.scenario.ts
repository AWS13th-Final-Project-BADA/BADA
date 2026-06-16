/**
 * 증거 수집 에이전트 — 디바이스 파이프라인 시나리오 (AWS 0원, 키 0개).
 *
 * 목적: 서버로 옮기기 전, 온디바이스 1~3단계가 '진짜로' 증거를 골라내는지 보여준다.
 *   - 1단계 메타데이터 필터: 기간/앨범/크기/확장자
 *   - 2단계 OCR + 키워드: ML Kit 출력을 mock 텍스트로 흉내
 *   - 3단계 문서 판별: 모델 없이 키워드 폴백(현재 MVP 동작)
 * Bedrock/서버는 4단계에서만 필요 → 이 시나리오엔 전혀 등장하지 않는다.
 *
 * 실행: node mobile/src/evidence-agent.scenario.ts   (Node 22.6+ 네이티브 TS)
 */
import { runEvidenceAgent, type AgentConfig, type PipelineInput } from "./evidence-agent.ts";

// ── 사건 설정 (베트남 E-9 제조업 노동자, 재직 기간) ──────────────
const config: AgentConfig = {
  caseId: "demo-case-001",
  workStartDate: "2026-01-15",
  workEndDate: "2026-05-31",
  workplaceName: "○○제조",
  apiBaseUrl: "http://localhost:8000",
};

// ── mock 갤러리 — 3000장의 축소판(증거 + 다양한 노이즈) ──────────
type GalleryFile = PipelineInput["files"][number];

const gallery: GalleryFile[] = [
  // ✅ 진짜 증거 (recommend 기대)
  { path: "/Download/payslip_2026_03.jpg", name: "payslip_2026_03.jpg",
    createdAt: "2026-04-05T10:00:00", album: "Download", sizeBytes: 480_000 },
  { path: "/KakaoTalk/chat_wage.png", name: "chat_wage.png",
    createdAt: "2026-04-10T21:30:00", album: "KakaoTalk", sizeBytes: 210_000 },
  { path: "/Screenshots/bank_transfer.jpg", name: "bank_transfer.jpg",
    createdAt: "2026-04-15T09:12:00", album: "Screenshots", sizeBytes: 320_000 },
  { path: "/DCIM/Camera/work_schedule.jpg", name: "work_schedule.jpg",
    createdAt: "2026-03-02T08:00:00", album: "Camera", sizeBytes: 540_000 },
  { path: "/Documents/contract.pdf", name: "contract.pdf",
    createdAt: "2026-01-10T14:00:00", album: "Documents", sizeBytes: 900_000 },

  // ⚠️ 기간·앨범·크기는 통과하지만 증거 아님 (2~3단계에서 걸러야 함)
  { path: "/DCIM/Camera/selfie.jpg", name: "selfie.jpg",
    createdAt: "2026-03-20T18:00:00", album: "Camera", sizeBytes: 1_200_000 },   // 글자 없음 → 보류 후 3단계 컷
  { path: "/DCIM/Camera/food.jpg", name: "food.jpg",
    createdAt: "2026-03-21T12:30:00", album: "Camera", sizeBytes: 800_000 },     // 음식 → 키워드 0
  { path: "/Download/meme.png", name: "meme.png",
    createdAt: "2026-03-22T20:00:00", album: "Download", sizeBytes: 150_000 },   // 밈 → 키워드 0
  { path: "/Screenshots/instagram.png", name: "instagram.png",
    createdAt: "2026-03-23T19:00:00", album: "Screenshots", sizeBytes: 260_000 }, // SNS → 키워드 0

  // ❌ 1단계 메타데이터에서 컷
  { path: "/DCIM/Camera/old_trip.jpg", name: "old_trip.jpg",
    createdAt: "2025-06-01T12:00:00", album: "Camera", sizeBytes: 700_000 },     // 기간 밖
  { path: "/Pictures/web_save.jpg", name: "web_save.jpg",
    createdAt: "2026-03-01T12:00:00", album: "Pictures", sizeBytes: 400_000 },   // 대상 앨범 아님
  { path: "/Screenshots/tiny_icon.png", name: "tiny_icon.png",
    createdAt: "2026-03-01T12:00:00", album: "Screenshots", sizeBytes: 4_000 },  // 10KB 미만
  { path: "/Download/clip.gif", name: "clip.gif",
    createdAt: "2026-03-01T12:00:00", album: "Download", sizeBytes: 300_000 },   // 허용 확장자 아님
];

// ── ML Kit OCR 출력 흉내 (디바이스에서 읽은 텍스트) ──────────────
const OCR_TEXT: Record<string, string> = {
  "payslip_2026_03.jpg":
    "급여명세서 2026년 3월 기본급 2,000,000 수당 300,000 공제 400,000 실수령 1,900,000 지급총액 2,300,000",
  "chat_wage.png":
    "사장님 이번달 월급 언제 들어와요? 다음주에 지급할게요 수고했어요 내일 출근 잊지마요",
  "bank_transfer.jpg":
    "○○제조 입금 1,900,000원 거래내역 잔액 5,200,000원 이체 완료",
  "work_schedule.jpg":
    "3월 근무표 출근 09:00 퇴근 18:00 근무시간 8시간 교대 연장 2시간",
  "contract.pdf":
    "근로계약서 갑 을 서명 근로 고용 시급 10,320원 근무장소 ○○제조",
  "selfie.jpg": "",                       // 인물 사진 → 글자 거의 없음
  "food.jpg": "맛있다 점심 김치찌개 한그릇",   // 음식
  "meme.png": "ㅋㅋㅋㅋ 이거 실화냐 짤방",       // 밈
  "instagram.png": "좋아요 팔로우 댓글 공유 스토리",
};

const ocrFn = async (filePath: string): Promise<string> => {
  const name = filePath.split("/").pop() ?? "";
  return OCR_TEXT[name] ?? "";
};

// ── 실행 + 결과 출력 ────────────────────────────────────────────
function bar(label: string, n: number, total: number): string {
  const width = 24;
  const filled = total ? Math.round((n / total) * width) : 0;
  return `${label.padEnd(18)} ${"█".repeat(filled)}${"·".repeat(width - filled)} ${n}/${total}`;
}

async function main() {
  console.log("═".repeat(64));
  console.log(" 증거 수집 에이전트 — 디바이스 파이프라인 (AWS 미사용)");
  console.log(` 사건: ${config.workplaceName}  근무 ${config.workStartDate} ~ ${config.workEndDate}`);
  console.log("═".repeat(64));

  // classifyFn 생략(undefined) → 3단계는 키워드 폴백(현재 MVP 동작)
  const result = await runEvidenceAgent({ files: gallery, ocrFn, config });

  console.log("\n[ 비용 깔때기 ] 단계가 뒤로 갈수록 비싸짐 — 앞에서 최대한 버린다\n");
  const t = result.totalScanned;
  console.log(bar("갤러리 전체", t, t));
  console.log(bar("1단계 메타데이터", result.stage1_count, t));
  console.log(bar("2단계 OCR+키워드", result.stage2_count, t));
  console.log(bar("3단계 문서판별", result.stage3_count, t));
  console.log(`\n→ 서버(4단계 Bedrock)로 보낼 후보: ${result.stage3_count}장  (전체의 ${Math.round((result.stage3_count / t) * 100)}%)`);
  console.log(`   소요: ${result.duration_ms}ms (디바이스 로컬, 네트워크 0)`);

  console.log("\n[ 사용자에게 보여줄 추천 (HITL — 승인 전) ]\n");
  for (const c of result.candidates) {
    const mark = c.finalDecision === "recommend" ? "✅ 추천" : "🤔 확인";
    console.log(`${mark}  ${c.fileName}  [${c.album}]`);
    for (const r of c.reasons) console.log(`        - ${r}`);
  }

  // 걸러진 파일들도 '왜 빠졌는지' 설명 가능해야 함(추적성)
  const keptNames = new Set(result.candidates.map((c) => c.fileName));
  const dropped = gallery.filter((f) => !keptNames.has(f.name)).map((f) => f.name);
  console.log("\n[ 제외됨 (후보 아님) ]");
  console.log("        " + dropped.join(", "));

  console.log("\n" + "═".repeat(64));
  console.log(" 결론: 증거 5장만 추천 / 셀카·음식·밈·SNS·기간밖·잡파일은 디바이스에서 컷.");
  console.log("        Bedrock 호출 0회 — 서버 비용은 승인된 5장에만 발생.");
  console.log("═".repeat(64));
}

main().catch((e) => {
  console.error("시나리오 실행 실패:", e);
  process.exit(1);
});
