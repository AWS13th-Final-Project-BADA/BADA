/**
 * 증거 수집 에이전트 — 4단계 파일 탐색 (Capacitor 네이티브 앱)
 *
 * 단계:
 *   1. 온디바이스 메타데이터 필터 (비용 0) — 기간+앨범
 *   2. 온디바이스 OCR + 키워드 매칭 (비용 0) — ML Kit
 *   3. 로컬 경량 모델로 문서/비문서 판별 (비용 0) — TFLite
 *   4. 서버 전송 → classify + OCR (비용 최소) — 승인 후
 *
 * 설계 원칙:
 *   - 비싼 순서대로 뒤로 배치
 *   - 사용자 동의(승인) 없이 서버 전송 금지 (HITL)
 *   - 모든 단계는 취소 가능 (AbortController)
 */

// ── 타입 정의 ──────────────────────────────────────────

export interface AgentConfig {
  caseId: string;
  workStartDate: string;   // ISO (사건의 근무 시작일)
  workEndDate?: string;    // ISO (근무 종료일, 없으면 오늘)
  workplaceName?: string;  // 사업장명 (키워드에 추가)
  apiBaseUrl: string;      // 서버 URL
}

export interface ScanCandidate {
  filePath: string;
  fileName: string;
  createdAt: string;       // ISO
  album: string;
  stage1_passed: boolean;  // 메타데이터 통과
  stage2_text?: string;    // 온디바이스 OCR 추출 텍스트
  stage2_keywords: string[]; // 매칭된 키워드
  stage2_passed: boolean;
  stage3_docType?: string; // 문서 판별 결과 (document/receipt/messenger/unknown)
  stage3_score?: number;   // 확률
  stage3_passed: boolean;
  finalDecision: 'recommend' | 'maybe' | 'exclude';
  reasons: string[];
}

export interface AgentResult {
  totalScanned: number;
  stage1_count: number;
  stage2_count: number;
  stage3_count: number;
  candidates: ScanCandidate[];
  duration_ms: number;
}

// ── 1단계: 메타데이터 필터 (비용 0) ──────────────────

const TARGET_ALBUMS = [
  'Screenshots', '스크린샷',
  'KakaoTalk', 'KakaoTalkPhoto', '카카오톡',
  'Download', '다운로드',
  'Camera', 'DCIM',
  'Documents', '문서',
];

/**
 * 날짜 범위 + 앨범(폴더)으로 1차 필터링.
 * Capacitor의 @capacitor-community/media 또는 네이티브 브릿지로 구현.
 */
export function filterByMetadata(
  files: Array<{ path: string; name: string; createdAt: string; album: string; sizeBytes: number }>,
  config: AgentConfig
): Array<typeof files[number]> {
  const startDate = new Date(config.workStartDate);
  const endDate = config.workEndDate ? new Date(config.workEndDate) : new Date();
  // 30일 여유 (계약서를 근무 전에 찍었을 수 있음)
  startDate.setDate(startDate.getDate() - 30);

  return files.filter(f => {
    // 날짜 범위
    const d = new Date(f.createdAt);
    if (d < startDate || d > endDate) return false;

    // 앨범(폴더) 확인
    const albumMatch = TARGET_ALBUMS.some(
      a => f.album.toLowerCase().includes(a.toLowerCase()) ||
           f.path.toLowerCase().includes(a.toLowerCase())
    );
    if (!albumMatch) return false;

    // 크기: 10KB 미만은 아이콘/캐시
    if (f.sizeBytes < 10_000) return false;

    // 확장자: 이미지/PDF만
    const ext = f.name.split('.').pop()?.toLowerCase() || '';
    if (!['jpg', 'jpeg', 'png', 'webp', 'heic', 'pdf'].includes(ext)) return false;

    return true;
  });
}

// ── 2단계: 온디바이스 OCR + 키워드 (비용 0) ──────────

// 한국어 핵심 키워드 (증거와 관련성 높은 단어)
const EVIDENCE_KEYWORDS_KO = [
  // 급여 관련
  '급여', '임금', '월급', '시급', '수당', '기본급', '실수령',
  '지급', '공제', '세전', '세후', '명세',
  // 계약 관련
  '계약', '근로', '고용', '갑', '을', '서명', '날인',
  // 입금 관련
  '입금', '출금', '이체', '잔액', '거래',
  // 근무 관련
  '출근', '퇴근', '근무', '교대', '연장',
  // 분쟁 관련
  '체불', '미지급', '노동', '신고',
];

/**
 * ML Kit/Vision 으로 추출된 텍스트에서 증거 키워드를 검색.
 * 키워드가 2개 이상 매칭되면 통과.
 */
export function matchKeywords(
  ocrText: string,
  config: AgentConfig
): { passed: boolean; matched: string[] } {
  if (!ocrText || ocrText.trim().length < 5) {
    // 텍스트를 아예 못 읽었으면 "보류"로 다음 단계에 넘김 (위음성 방지)
    return { passed: true, matched: ['(텍스트 미인식 — 보류)'] };
  }

  const text = ocrText.toLowerCase();
  const allKeywords = [...EVIDENCE_KEYWORDS_KO];
  // 사업장명이 있으면 키워드에 추가
  if (config.workplaceName) {
    allKeywords.push(config.workplaceName.toLowerCase());
  }

  const matched = allKeywords.filter(kw => text.includes(kw));
  return { passed: matched.length >= 2, matched };
}

// ── 3단계: 문서 판별 (경량 모델, 비용 0) ─────────────

export type DocType = 'document' | 'receipt' | 'messenger' | 'photo' | 'unknown';

/**
 * TFLite/CoreML 모델의 출력을 해석.
 * 실제 모델 추론은 네이티브 브릿지에서 수행하고 결과만 여기서 받는다.
 *
 * 모델이 없는 환경(MVP)에서는 stage2 키워드 매칭 결과를 기반으로 대체 판정.
 */
export function judgeDocType(
  modelOutput: { type: DocType; confidence: number } | null,
  stage2Matched: string[]
): { passed: boolean; docType: DocType; score: number } {
  // 모델 결과가 있으면 사용
  if (modelOutput) {
    const { type, confidence } = modelOutput;
    const isDoc = ['document', 'receipt', 'messenger'].includes(type);
    return { passed: isDoc && confidence > 0.5, docType: type, score: confidence };
  }

  // MVP 폴백: 모델 없으면 stage2 키워드 수로 대체 판정
  const score = Math.min(stage2Matched.length / 5, 1.0);
  const docType: DocType = stage2Matched.length >= 3 ? 'document' : 'unknown';
  return { passed: score >= 0.4, docType, score };
}

// ── 전체 파이프라인 실행 ─────────────────────────────

export interface PipelineInput {
  /** 디바이스에서 읽어온 파일 목록 (네이티브 브릿지가 제공) */
  files: Array<{
    path: string;
    name: string;
    createdAt: string;
    album: string;
    sizeBytes: number;
  }>;
  /** 각 파일에 대해 네이티브 OCR을 수행하는 콜백 (ML Kit/Vision) */
  ocrFn: (filePath: string) => Promise<string>;
  /** 경량 분류 모델 추론 콜백 (없으면 null → 폴백) */
  classifyFn?: (filePath: string) => Promise<{ type: DocType; confidence: number } | null>;
  config: AgentConfig;
  /** 진행 상황 콜백 (UI 업데이트용) */
  onProgress?: (stage: number, current: number, total: number) => void;
}

/**
 * 4단계 증거 수집 에이전트 전체 실행.
 * 반환: 최종 후보 목록 + 통계.
 * 서버 전송(4단계)은 포함하지 않음 — 사용자 승인 후 별도 호출.
 */
export async function runEvidenceAgent(input: PipelineInput): Promise<AgentResult> {
  const startTime = Date.now();
  const { files, ocrFn, classifyFn, config, onProgress } = input;

  // ── 1단계: 메타데이터 ──
  const stage1 = filterByMetadata(files, config);
  onProgress?.(1, stage1.length, files.length);

  // ── 2단계: OCR + 키워드 (병렬 4개씩) ──
  const stage2Results: Array<{ file: typeof stage1[number]; text: string; kw: ReturnType<typeof matchKeywords> }> = [];
  const batchSize = 4;
  for (let i = 0; i < stage1.length; i += batchSize) {
    const batch = stage1.slice(i, i + batchSize);
    const results = await Promise.all(
      batch.map(async f => {
        const text = await ocrFn(f.path);
        const kw = matchKeywords(text, config);
        return { file: f, text, kw };
      })
    );
    stage2Results.push(...results);
    onProgress?.(2, Math.min(i + batchSize, stage1.length), stage1.length);
  }
  const stage2Passed = stage2Results.filter(r => r.kw.passed);

  // ── 3단계: 문서 판별 ──
  const candidates: ScanCandidate[] = [];
  for (const item of stage2Passed) {
    const modelOut = classifyFn ? await classifyFn(item.file.path) : null;
    const judge = judgeDocType(modelOut, item.kw.matched);

    const reasons: string[] = [];
    if (item.kw.matched.length > 0) {
      reasons.push(`키워드: ${item.kw.matched.slice(0, 5).join(', ')}`);
    }
    reasons.push(`문서 유형: ${judge.docType} (${Math.round(judge.score * 100)}%)`);

    let finalDecision: ScanCandidate['finalDecision'] = 'exclude';
    if (judge.passed && item.kw.matched.length >= 3) {
      finalDecision = 'recommend';
    } else if (judge.passed || item.kw.matched.length >= 2) {
      finalDecision = 'maybe';
    }

    candidates.push({
      filePath: item.file.path,
      fileName: item.file.name,
      createdAt: item.file.createdAt,
      album: item.file.album,
      stage1_passed: true,
      stage2_text: item.text.slice(0, 200),
      stage2_keywords: item.kw.matched,
      stage2_passed: item.kw.passed,
      stage3_docType: judge.docType,
      stage3_score: judge.score,
      stage3_passed: judge.passed,
      finalDecision,
      reasons,
    });
    onProgress?.(3, candidates.length, stage2Passed.length);
  }

  // exclude 제외, recommend 우선 정렬
  const sorted = candidates
    .filter(c => c.finalDecision !== 'exclude')
    .sort((a, b) => {
      if (a.finalDecision === 'recommend' && b.finalDecision !== 'recommend') return -1;
      if (b.finalDecision === 'recommend' && a.finalDecision !== 'recommend') return 1;
      return (b.stage2_keywords.length) - (a.stage2_keywords.length);
    });

  return {
    totalScanned: files.length,
    stage1_count: stage1.length,
    stage2_count: stage2Passed.length,
    stage3_count: sorted.length,
    candidates: sorted,
    duration_ms: Date.now() - startTime,
  };
}
