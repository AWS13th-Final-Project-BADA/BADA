/** 증거(evidence) 타입 — backend evidences.py. */
import type { Category, FileType } from "@/shared/types";

/** POST /cases/{id}/evidences 응답 */
export interface PresignResult {
  evidence_id: string;
  upload_url: string | null;
  file_key: string;
}

/** GET /cases/{id}/evidences 응답 항목 */
export interface EvidenceItem {
  id: string;
  file_name: string;
  category: string;
  ocr_status: string | null;
}

export const CATEGORY_FILETYPE: Record<Category, FileType> = {
  contract: "pdf",
  schedule: "image",
  payment: "image",
  chat: "image",
  statement: "pdf",
  other: "image",
};
