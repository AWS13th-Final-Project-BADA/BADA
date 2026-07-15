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

  return { evidenceId, via: "multipart" };
}

