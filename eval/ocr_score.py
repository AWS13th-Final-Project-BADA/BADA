"""OCR 필드 단위 정확도 측정 — gold 엔티티 대비 추출 엔티티 비교.

왜 필요? 지금까지 정확도가 '감'이었다. 실제 샘플에 정답(gold)을 달아 두고
필드별 정확률을 숫자로 재면, 이후 프롬프트/엔진 개선의 기준선이 생긴다.

라벨 형식(eval/dataset/ocr/*.json):
{
  "case_id": "stmt_001",
  "gold_entities":      { ... 사람이 적은 정답 ... },
  "extracted_entities": { ... OCR이 뽑은 값(오프라인 비교용; 없으면 raw_file로 라이브 추출) ... },
  "category": "statement",          # (선택) 라이브 추출 시 사용
  "raw_file": "dataset/raw/stmt_001.jpg"  # (선택) 있으면 OCR을 실제로 돌려 비교
}

집계는 'gold에 값이 있는 필드'만 분모로 센다(= recall 기준: 정답을 OCR이 맞췄나).

실행:
  python ocr_score.py dataset/ocr                 # 오프라인(extracted_entities 비교)
  python ocr_score.py dataset/ocr --live          # raw_file에 OCR 실제 실행 후 비교(AWS 필요)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_SCALARS = ["hourly_wage", "monthly_wage", "work_days", "pay_date",
            "contract_start", "contract_end", "signed",
            "overtime_hours", "night_hours", "holiday_hours",
            "workplace_name", "employer_name"]


def _empty(v):
    return v is None or v == "" or v == []


def _norm(s) -> str:
    return re.sub(r"\s+", "", str(s)).lower()


def _eq_num(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return _norm(a) == _norm(b)


def _score_amounts(gold: list, pred: list) -> tuple[int, int]:
    """gold amount 각각에 대해 같은 label의 pred value가 일치하면 정답."""
    correct = 0
    pred_by = {_norm(p.get("label")): p.get("value") for p in (pred or [])}
    for g in gold or []:
        pv = pred_by.get(_norm(g.get("label")))
        if pv is not None and _eq_num(pv, g.get("value")):
            correct += 1
    return correct, len(gold or [])


def _score_pairs(gold: list, pred: list, key: str, val: str) -> tuple[int, int]:
    correct = 0
    pred_by = {_norm(p.get(key)): p.get(val) for p in (pred or [])}
    for g in gold or []:
        pv = pred_by.get(_norm(g.get(key)))
        if pv is not None and _eq_num(pv, g.get(val)):
            correct += 1
    return correct, len(gold or [])


def _score_set(gold: list, pred: list) -> tuple[int, int]:
    ps = {_norm(x) for x in (pred or [])}
    correct = sum(1 for g in (gold or []) if _norm(g) in ps)
    return correct, len(gold or [])


def score_one(gold: dict, pred: dict) -> dict:
    """단일 케이스 필드별 (correct, counted). gold에 값이 있는 필드만 센다."""
    fields: dict[str, tuple[int, int]] = {}
    for f in _SCALARS:
        if _empty(gold.get(f)):
            continue
        ok = (not _empty(pred.get(f))) and _eq_num(pred.get(f), gold.get(f)) \
            if f not in ("signed",) else pred.get(f) == gold.get(f)
        fields[f] = (1 if ok else 0, 1)
    if gold.get("amounts"):
        fields["amounts"] = _score_amounts(gold["amounts"], pred.get("amounts", []))
    if gold.get("deductions"):
        fields["deductions"] = _score_pairs(gold["deductions"], pred.get("deductions", []), "name", "amount")
    if gold.get("dates"):
        fields["dates"] = _score_set(gold["dates"], pred.get("dates", []))
    return fields


def _live_extract(label: dict, base: Path) -> dict:
    sys.path.insert(0, str(base.parents[0] / "worker"))
    from providers.ocr import get_ocr  # worker
    data = (base / label["raw_file"]).read_bytes()
    out = get_ocr(label.get("category", "other")).extract(data, label.get("category", "other"))
    return out.get("entities", {})


def main(folder: str, live: bool = False):
    base = Path(__file__).resolve().parent
    files = sorted((base / folder).glob("*.json"))
    if not files:
        print(f"라벨 파일 없음: {folder}")
        return
    agg: dict[str, list[int]] = {}
    n_case = 0
    for f in files:
        label = json.loads(f.read_text(encoding="utf-8"))
        gold = label.get("gold_entities", {})
        pred = _live_extract(label, base) if live else label.get("extracted_entities", {})
        fields = score_one(gold, pred)
        n_case += 1
        c = sum(v[0] for v in fields.values())
        t = sum(v[1] for v in fields.values())
        print(f"[{label['case_id']}] {c}/{t}  " +
              "  ".join(f"{k}:{v[0]}/{v[1]}" for k, v in fields.items()))
        for k, (cc, tt) in fields.items():
            a = agg.setdefault(k, [0, 0])
            a[0] += cc
            a[1] += tt
    print("\n=== 필드별 정확도 ===")
    tot_c = tot_t = 0
    for k, (cc, tt) in sorted(agg.items()):
        pct = 100 * cc / tt if tt else 0
        print(f"  {k:16s} {cc:3d}/{tt:<3d}  {pct:5.1f}%")
        tot_c += cc
        tot_t += tt
    overall = 100 * tot_c / tot_t if tot_t else 0
    print(f"  {'전체':16s} {tot_c:3d}/{tot_t:<3d}  {overall:5.1f}%  ({n_case}건)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else "dataset/ocr", live="--live" in sys.argv)
