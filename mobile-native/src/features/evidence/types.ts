import type { Category, FileType } from "@/shared/types";

export interface PresignResult {
  evidence_id: string;
  upload_url: string | null;
  file_key: string;
}

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
