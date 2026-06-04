"""내 데이터로 분석 파이프라인을 직접 테스트.

사용법 (worker 폴더에서):
    python try_case.py sample_case.json

이미지 OCR(Bedrock)은 아직 스텁이므로, 추출됐다고 가정한 값을 JSON으로 직접 넣는다.
규칙 엔진(차액/공제/누락/GPS 교차검증)이 실제로 어떤 결과를 내는지 사람이 읽기 좋게 출력한다.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

from pipeline import process_case


def _parse(ctx: dict) -> dict:
    for lg in ctx.get("gps_logs", []):
        if isinstance(lg.get("ts"), str):
            lg["ts"] = datetime.fromisoformat(lg["ts"])
    ctx["chat_arrivals"] = [
        datetime.fromisoformat(s) if isinstance(s, str) else s
        for s in ctx.get("chat_arrivals", [])
    ]
    return ctx


def _won(n):
    return "-" if n is None else f"{n:,}원"


def main(path: str):
    ctx = _parse(json.loads(open(path, encoding="utf-8").read()))
    r = process_case("try", ctx)

    print("=" * 50)
    print(" BADA 분석 결과 (규칙 엔진)")
    print("=" * 50)
    print(f" 기대 급여   : {_won(r['total_expected_wage'])}")
    print(f" 실제 수령   : {_won(r['total_received_wage'])}")
    print(f" 미지급 의심 : {_won(r['suspected_unpaid'])}   (확정 아님, 확인 필요)")
    print("-" * 50)
    print(" 공제 항목 정리")
    for d in r["deduction_items"]:
        print(f"   - {d['name']} ({d['category']}) {_won(d['amount'])}  : {d['check']}")
    print(f"   공제 합계: {_won(r['deduction_total'])}")
    print("-" * 50)
    print(" 더 준비하면 좋은 자료(누락)")
    for m in r["missing_evidences"]:
        print(f"   - [{m['item']}] {m['reason']}")
    if r["gps"]:
        print("-" * 50)
        print(" GPS 정황")
        print(f"   판정된 핑: {r['gps']['tagged_count']}건, 카톡 도착-근무지 교차일치: {r['gps']['cross_matches']}건")
    if r["notes"]:
        print("-" * 50)
        for n in r["notes"]:
            print(f" * {n}")
    print("=" * 50)
    print(" 본 자료는 법률자문이 아닌 상담 준비용 정리입니다.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sample_case.json")
