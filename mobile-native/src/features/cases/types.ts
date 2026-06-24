/** 사건(cases) 타입 — backend cases.py / schemas.CaseCreate. */

/** GET /cases, GET /cases/{id} 응답 (cases.py _dict) */
export interface Case {
  id: string;
  workplace_name: string | null;
  employer_name: string | null;
  work_start_date: string | null;
  work_end_date: string | null;
  agreed_hourly_wage: number | null;
  agreed_weekly_hours: number | null;
  issue_types: string[];
  status: string;
}

/** POST /cases 요청 (schemas.CaseCreate) */
export interface CaseCreate {
  workplace_name?: string | null;
  employer_name?: string | null;
  work_start_date?: string | null;
  work_end_date?: string | null;
  agreed_hourly_wage?: number | null;
  agreed_weekly_hours?: number | null;
  issue_types?: string[];
}

export const ISSUE_TYPES = [
  "wage_unpaid",
  "deduction",
  "overtime",
  "severance",
  "other",
] as const;

export const ISSUE_LABELS: Record<string, string> = {
  wage_unpaid: "임금 미지급",
  deduction: "임의 공제",
  overtime: "연장·야간수당",
  severance: "퇴직금",
  other: "기타",
};
