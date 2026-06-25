import { API_BASE, fetchApi, getToken, isDemoAccessToken } from "@/lib/api";
import type { Category, FileType } from "@/shared/types";
import type { PresignResult } from "@/features/evidence/types";

export interface PickedFile {
  uri: string;
  name: string;
  mimeType: string;
}

export async function uploadEvidence(
  caseId: string,
  file: PickedFile,
  category: Category,
  fileType: FileType
): Promise<{ evidenceId: string; via: "s3" | "multipart" }> {
  const presign = await fetchApi<PresignResult>(`/cases/${caseId}/evidences`, {
    method: "POST",
    body: JSON.stringify({
      file_name: file.name,
      file_type: fileType,
      category,
      // 실제 MIME을 함께 전달 → 백엔드 presign 서명과 아래 S3 PUT의 Content-Type이 일치(허용: image/jpeg·png, application/pdf)
      content_type: file.mimeType,
    }),
  });

  const token = await getToken();
  if (isDemoAccessToken(token)) {
    return { evidenceId: presign.evidence_id, via: "multipart" };
  }

  if (presign.upload_url) {
    const blob = await (await fetch(file.uri)).blob();
    const put = await fetch(presign.upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.mimeType },
      body: blob,
    });
    if (!put.ok) throw new Error(`S3 PUT failed: ${put.status}`);
    return { evidenceId: presign.evidence_id, via: "s3" };
  }

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
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);

  return { evidenceId: presign.evidence_id, via: "multipart" };
}
