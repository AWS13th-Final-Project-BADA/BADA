"""평가 하네스 — gold 라벨 대비 규칙엔진 정확도 측정.

사용: python harness.py dataset/samples
규칙엔진(worker/rules)을 그대로 호출하므로, 계산이 라벨과 일치하는지 회귀 검증도 된다.
LLM/OCR 정확도(엔티티 추출)는 W2에 추출값 vs 정답 비교를 추가한다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# worker 패키지 임포트 경로
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worker"))

from rules import deductions as ded  # noqa: E402
from rules import missing, wage  # noqa: E402


def evaluate_case(label: dict) -> dict:
    i = label["inputs"]
    exp = label["expected"]

    w = wage.compute_unpaid(i.get("agreed_hourly_wage"), i.get("worked_hours", []), i.get("deposits", []))
    classified = ded.classify_deductions(i.get("raw_deductions", []))
    miss = missing.check_missing(set(i.get("present_categories", [])))

    got_categories = sorted({c["category"] for c in classified})
    got_missing = sorted({m["item"] for m in miss})

    checks = {
        "expected_wage_ok": w.total_expected_wage == exp.get("total_expected_wage"),
        "suspected_unpaid_ok": w.suspected_unpaid == exp.get("suspected_unpaid"),
        "deduction_categories_ok": got_categories == sorted(set(exp.get("deduction_categories", []))),
        "missing_ok": got_missing == sorted(set(exp.get("missing_items", []))),
    }
    return {"case_id": label["case_id"], "checks": checks, "passed": all(checks.values()),
            "got": {"expected_wage": w.total_expected_wage, "suspected": w.suspected_unpaid,
                    "categories": got_categories, "missing": got_missing}}


def main(folder: str):
    files = sorted(Path(folder).glob("*.json"))
    if not files:
        print(f"라벨 파일 없음: {folder}")
        return
    results = [evaluate_case(json.loads(f.read_text(encoding="utf-8"))) for f in files]
    n_pass = sum(r["passed"] for r in results)
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"[{mark}] {r['case_id']}  {r['checks']}")
        if not r["passed"]:
            print(f"        got = {r['got']}")
    print(f"\n{n_pass}/{len(results)} cases passed")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dataset/samples")
