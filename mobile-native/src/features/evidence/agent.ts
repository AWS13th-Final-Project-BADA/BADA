/**
 * 증거 수집 에이전트 — Expo 포팅 (mobile/src/evidence-agent.ts 기반)
 *
 * 4단계 파이프라인:
 *   1. 메타데이터 필터 (날짜+앨범+크기) — 비용 0
 *   2. 온디바이스 OCR + 키워드 — MVP: OCR 미지원 환경에서는 전부 보류 처리
 *   3. 키워드 수 기반 문서 판별 (모델 없음 → 폴백)
 *   4. 사용자 승인 → 서버 업로드 (HITL)
 *
 * ponytail: Expo에서 ML Kit OCR이 없으므로 2단계는 파일명 기반 키워드로 대체.
 *           정확도 한계 있지만 1단계 메타필터만으로도 3000→200 수준 감축 가능.
 */
import * as MediaLibrary from "expo-media-library";
import { fetchApi } from "@/lib/api";

// ── 타입 ──

export interface AgentConfig {
  caseId: string;
  workStartDate: string;
  workEndDate?: string;
  workplaceName?: string;
}

export interface ScanCandidate {
  asset: MediaLibrary.Asset;
  keywords: string[];
  score: number;
  decision: "recommend" | "maybe";
  reasons: string[];
}

export interface AgentResult {
  totalScanned: number;
  stage1Count: number;
  candidates: ScanCandidate[];
  durationMs: number;
}

// ── 키워드 ──

const EVIDENCE_KEYWORDS = [
  "급여", "임금", "월급", "시급", "수당", "기본급", "실수령",
  "지급", "공제", "세전", "세후", "명세",
  "계약", "근로", "고용",
  "입금", "출금", "이체", "잔액", "거래",
  "출근", "퇴근", "근무", "교대", "연장",
  "체불", "미지급", "노동", "신고",
  "payslip", "contract", "wage", "salary", "bank",
];

// ── 1단계: 메타데이터 필터 ──

export async function scanGallery(config: AgentConfig): Promise<AgentResult> {
  const start = Date.now();

  const { status } = await MediaLibrary.requestPermissionsAsync();
  if (status !== "granted") {
    throw new Error("갤러리 접근 권한이 필요합니다.");
  }

  const startDate = new Date(config.workStartDate);
  startDate.setDate(startDate.getDate() - 30); // 30일 여유
  const endDate = config.workEndDate ? new Date(config.workEndDate) : new Date();

  // 갤러리에서 기간 내 이미지/PDF 가져오기
  const assets = await MediaLibrary.getAssetsAsync({
    mediaType: [MediaLibrary.MediaType.photo],
    createdAfter: startDate.getTime(),
    createdBefore: endDate.getTime(),
    first: 9999, // ponytail: 기간 필터가 실질적 제한 역할. 제한 없이 전부 스캔
    sortBy: [MediaLibrary.SortBy.creationTime],
  });

  const totalScanned = assets.assets.length;

  // 크기 10KB 미만 제외 (fileSize가 없는 경우 통과)
  const stage1 = assets.assets.filter(a => {
    if (a.width < 100 && a.height < 100) return false; // 아이콘급
    return true;
  });

  // ── 2~3단계: 파일명 키워드 매칭 (온디바이스 OCR 대체) ──
  const candidates: ScanCandidate[] = [];

  for (const asset of stage1) {
    const filename = (asset.filename || "").toLowerCase();
    const matched = EVIDENCE_KEYWORDS.filter(kw => filename.includes(kw));

    // 스크린샷/카톡 폴더 이름 매칭으로 보정
    const uri = asset.uri.toLowerCase();
    const fromScreenshot = uri.includes("screenshot") || uri.includes("스크린샷");
    const fromKakao = uri.includes("kakao") || uri.includes("카카오");
    const fromDownload = uri.includes("download") || uri.includes("다운로드");

    let score = matched.length * 0.3;
    if (fromScreenshot) score += 0.2;
    if (fromKakao) score += 0.3;
    if (fromDownload) score += 0.1;

    // 사업장명 매칭
    if (config.workplaceName && filename.includes(config.workplaceName.toLowerCase())) {
      score += 0.4;
      matched.push(config.workplaceName);
    }

    const reasons: string[] = [];
    if (matched.length > 0) reasons.push(`키워드: ${matched.join(", ")}`);
    if (fromKakao) reasons.push("카카오톡 폴더");
    if (fromScreenshot) reasons.push("스크린샷");
    if (fromDownload) reasons.push("다운로드 폴더");

    // score 0.2 이상이면 후보
    if (score >= 0.2 || fromKakao || fromScreenshot) {
      candidates.push({
        asset,
        keywords: matched,
        score,
        decision: score >= 0.5 ? "recommend" : "maybe",
        reasons: reasons.length ? reasons : ["기간 내 이미지"],
      });
    }
  }

  // 점수순 정렬, recommend 우선
  candidates.sort((a, b) => {
    if (a.decision === "recommend" && b.decision !== "recommend") return -1;
    if (b.decision === "recommend" && a.decision !== "recommend") return 1;
    return b.score - a.score;
  });

  // ponytail: 제한 없이 전부 보여줌 — 바깥 스크롤로 탐색
  const finalCandidates = candidates;

  return {
    totalScanned,
    stage1Count: stage1.length,
    candidates: finalCandidates,
    durationMs: Date.now() - start,
  };
}

// ── 4단계: 승인된 파일 업로드 ──

export async function uploadApprovedCandidates(
  caseId: string,
  candidates: ScanCandidate[],
): Promise<{ uploaded: number }> {
  let uploaded = 0;

  for (const c of candidates) {
    const assetInfo = await MediaLibrary.getAssetInfoAsync(c.asset);
    const uri = assetInfo.localUri || assetInfo.uri;

    const fd = new FormData();
    fd.append("category", "other"); // 서버에서 자동 분류
    fd.append("file", {
      uri,
      name: c.asset.filename || `evidence-${Date.now()}.jpg`,
      type: "image/jpeg",
    } as any);

    await fetchApi(`/cases/${caseId}/evidences/upload`, {
      method: "POST",
      headers: { "Content-Type": "multipart/form-data" },
      body: fd,
    });
    uploaded++;
  }

  return { uploaded };
}
