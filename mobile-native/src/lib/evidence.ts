/**
 * 증거 업로드 로직 — backend 계약에 맞춤.
 *
 * 1) POST /cases/{id}/evidences  (PresignedUploadRequest) → {evidence_id, upload_url, file_key}
 * 2) upload_url 있으면 → S3로 직접 PUT (권장 경로)
 *    upload_url 없으면(로컬/미설정) → multipart POST /cases/{id}/evidences/upload 폴백
 */
import { fetchApi, API_BASE, getToken } from "./api";
import type { Category, FileType, PresignResult } from "./types";

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
  // 1) presign 요청 + Evidence 레코드 생성
  const presign = await fetchApi<PresignResult>(`/cases/${caseId}/evidences`, {
    method: "POST",
    body: JSON.stringify({
      file_name: file.name,
      file_type: fileType,
      category,
    }),
  });

  // 2-a) S3 직접 PUT
  if (presign.upload_url) {
    const blob = await (await fetch(file.uri)).blob();
    const put = await fetch(presign.upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.mimeType },
      body: blob,
    });
    if (!put.ok) throw new Error(`S3 PUT 실패: ${put.status}`);
    return { evidenceId: presign.evidence_id, via: "s3" };
  }

  // 2-b) multipart 폴백 (백엔드가 직접 저장)
  const token = await getToken();
  const fd = new FormData();
  fd.append("category", category);
  // RN FormData 파일 형식
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
  if (!res.ok) throw new Error(`업로드 실패: ${res.status}`);
  return { evidenceId: presign.evidence_id, via: "multipart" };
}
