import { API_BASE, fetchApi, getToken } from "@/lib/api";
import type { Category, FileType } from "@/shared/types";

export interface PickedFile {
  uri: string;
  name: string;
  mimeType: string;
}

export async function uploadEvidence(
  caseId: string,
  file: PickedFile,
  category: Category,
  _fileType: FileType
): Promise<{ evidenceId: string; via: "multipart" }> {
  const token = await getToken();

  const fd = new FormData();
  fd.append("category", category);
  fd.append("file", {
    uri: file.uri,
    name: file.name,
    type: file.mimeType,
  } as any);

  const res = await fetch(`${API_BASE}/cases/${caseId}/evidences/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: fd,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Upload failed: ${res.status} ${body}`);
  }

  const body = await res.json().catch(() => ({}));
  const evidenceId = body.id || body.evidence_id || `uploaded-${Date.now()}`;

  // 업로드 완료 → OCR 추출 트리거 (비동기, 실패해도 업로드는 성공)
  await triggerExtract(caseId);

  return { evidenceId, via: "multipart" };
}

/**
 * OCR 추출 트리거 — 업로드된 증거에 대해 비동기 OCR 실행 요청.
 * 실패해도 업로드 결과에는 영향 없음 (사용자가 수동으로 재시도 가능).
 */
async function triggerExtract(caseId: string): Promise<void> {
  try {
    await fetchApi(`/cases/${caseId}/evidences/extract`, { method: "POST" });
  } catch {
    // OCR 트리거 실패는 무시 — 분석 시 재시도 가능
  }
}
