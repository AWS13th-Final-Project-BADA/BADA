/** 분석(analysis) 타입 — backend schemas_report.py (AnalysisReport). */
import type { Confidence } from "@/shared/types";

export interface Wage {
  currency: string;
  computable: boolean;
  agreed_hourly: number | null;
  expected: number | null;
  received: number | null;
  suspected_unpaid: number | null;
  basis: string | null;
  notes: string[];
}
export interface Deduction {
  name: string;
  category: string;
  amount: number;
  currency: string;
  sources: string[];
  verify: string;
}
export interface Finding {
  type: string;
  severity: Confidence;
  message: string;
  amount: number | null;
}
export interface Legal {
  min_wage: { year: number; hourly: number };
  findings: Finding[];
}
export interface TimelineItem {
  date: string | null;
  type: string;
  text: string;
  text_translated: string | null;
  source_evidence_id: string | null;
  confidence: Confidence;
}
export interface MissingItem {
  item: string;
  reason: string;
}
export interface Narrative {
  summary: string;
  disclaimer: string;
}
export interface AnalysisReport {
  schema_version: string;
  case: {
    id: string;
    workplace: string | null;
    employer: string | null;
    issue_types: string[];
  };
  wage: Wage;
  deductions: Deduction[];
  legal: Legal;
  timeline: TimelineItem[];
  missing: MissingItem[];
  narrative: Narrative;
  meta: { generated_at: string | null; lang: string; provider_mode: string };
}
