/**
 * 공유 기본 타입(primitives) — 여러 기능이 공통으로 쓰는 enum류.
 * 백엔드 schemas.py·schemas_report.py 와 1:1.
 */

export type Category =
  | "contract"
  | "schedule"
  | "payment"
  | "chat"
  | "statement"
  | "other";

export type FileType = "image" | "pdf" | "text";
export type Confidence = "high" | "medium" | "low";
