"""증거 수집 에이전트 — 단계적 필터로 '싸게 분류, 비싼 OCR은 최소'.

비용 원칙(단계가 뒤로 갈수록 비싸짐):
  1) 분류(classify)   : 형태만 본다. 섬네일로도 충분. 스캔 단계에서 다량 처리.
  2) OCR + 키워드검증 : 실제 글자를 읽는다. 비싸다 → '관련' + '승인' 대상만.

그래서 두 모드:
  - assess_scan()  : 분류만(OCR X). 많은 파일을 싸게 훑어 후보를 추린다.
  - assess_deep()  : 분류 + OCR + 키워드 교차검증. 1장을 정밀 확인(정확성 3종).

설계 원칙(architecture.md): 자동 '확정'하지 않는다. 최종 등록은 사람이 승인(HITL).
"""
from __future__ import annotations

from providers import classify as classify_mod
from providers.ocr import get_ocr
from rules.category_keywords import verify_category

# 최종 추천 등급
DECISION_AUTO = "auto_accept"      # 강한 신호 → 체크된 채로 추천
DECISION_REVIEW = "needs_review"   # 애매/불일치 → 사용자 확인 필요
DECISION_REJECT = "rejected"       # 무관 이미지 → 후보에서 제외


def assess_scan(image_bytes: bytes) -> dict:
    """[싼 단계] 분류만 수행(OCR X). 스캔 단계에서 다량 파일을 빠르게 추린다.

    반환:
      {category, decision, confidence, alternative, reasons, classify}
    무관(irrelevant)은 rejected, 그 외는 분류 신뢰도 그대로 등급화.
    """
    cls = classify_mod.classify(image_bytes)
    category = cls.get("category", "other")
    base_conf = cls.get("confidence", "low")
    relevant = cls.get("relevant", True)
    reasons = [f"[형태] {cls['reason']}"] if cls.get("reason") else []

    if not relevant or category == "irrelevant":
        return {
            "category": "irrelevant",
            "decision": DECISION_REJECT,
            "confidence": "high" if base_conf == "high" else "medium",
            "alternative": None,
            "reasons": reasons + ["임금체불과 무관한 이미지로 보여 제외했어요."],
            "classify": cls,
        }

    # 분류만으로는 'high'여도 auto 확정하지 않는다(내용 미확인) → review 권장.
    # high는 review지만 우선순위 높게, medium/low는 review.
    decision = DECISION_REVIEW
    return {
        "category": category,
        "decision": decision,
        "confidence": base_conf,
        "alternative": cls.get("alternative"),
        "reasons": reasons + ["내용(OCR) 확인 전 추천이에요. 맞는지 확인해 주세요."],
        "classify": cls,
    }


def assess_deep(image_bytes: bytes) -> dict:
    """[비싼 단계] 분류 + OCR + 키워드 교차검증 (정확성 3종). 1장 정밀 확인용.

    스캔에서 추려 '승인 대상'이 된 파일, 또는 사용자가 정밀 확인을 원할 때 사용.
    """
    reasons: list[str] = []

    # 1단계: 형태 분류
    cls = classify_mod.classify(image_bytes)
    category = cls.get("category", "other")
    base_conf = cls.get("confidence", "low")
    relevant = cls.get("relevant", True)
    if cls.get("reason"):
        reasons.append(f"[형태] {cls['reason']}")

    if not relevant or category == "irrelevant":
        return {
            "category": "irrelevant", "decision": DECISION_REJECT,
            "confidence": "high" if base_conf == "high" else "medium",
            "classify": cls, "keyword_check": None, "raw_text": "",
            "reasons": reasons + ["임금체불과 무관한 이미지로 보여 제외했어요."],
        }

    # 2단계: OCR(실제 글자)
    raw_text = ""
    try:
        ocr_out = get_ocr(category).extract(image_bytes, category)
        raw_text = (ocr_out or {}).get("raw_text", "") or ""
    except Exception as e:  # noqa: BLE001
        reasons.append(f"[내용] OCR 실패로 내용 대조를 못 했어요({str(e)[:60]}).")

    # 3단계: 키워드 교차검증(규칙)
    kw = verify_category(category, raw_text)
    if kw.get("note"):
        reasons.append(f"[내용] {kw['note']}")

    decision, final_conf = _decide(base_conf, kw, cls)
    return {
        "category": category, "decision": decision, "confidence": final_conf,
        "classify": cls, "keyword_check": kw, "raw_text": raw_text,
        "reasons": reasons,
    }


def assess_batch(images: list[tuple[str, bytes]]) -> dict:
    """[스캔 단계 배치] 여러 파일을 분류만으로 빠르게 훑어 등급별로 묶는다.

    images: [(file_name, image_bytes), ...]
    반환: {
      "candidates": [{file_name, category, decision, confidence, alternative, reasons}],
      "summary": {auto_accept, needs_review, rejected},
      "recommended": [관련 후보 file_name],  # rejected 제외
    }
    OCR은 돌리지 않는다(비용 절감). 정밀 확인은 승인 후 OCR 단계에서.
    """
    candidates: list[dict] = []
    summary = {DECISION_AUTO: 0, DECISION_REVIEW: 0, DECISION_REJECT: 0}

    for file_name, data in images:
        res = assess_scan(data)
        summary[res["decision"]] = summary.get(res["decision"], 0) + 1
        candidates.append({
            "file_name": file_name,
            "category": res["category"],
            "decision": res["decision"],
            "confidence": res["confidence"],
            "alternative": res.get("alternative"),
            "reasons": res["reasons"],
        })

    recommended = [c["file_name"] for c in candidates if c["decision"] != DECISION_REJECT]
    return {"candidates": candidates, "summary": summary, "recommended": recommended}


def _decide(base_conf: str, kw: dict, cls: dict) -> tuple[str, str]:
    """형태 신뢰도 + 키워드 검증을 합쳐 최종 등급/신뢰도 산출(보수적: 애매하면 사람에게)."""
    if kw.get("conflict"):
        return DECISION_REVIEW, "low"
    if cls.get("multiple_docs") or not cls.get("readable", True):
        return DECISION_REVIEW, "low"

    agree = kw.get("agree", False)
    has_text = bool((kw.get("category_score", 0) or 0) > 0 or kw.get("best_category"))

    if base_conf == "high":
        if agree:
            return DECISION_AUTO, "high"
        return DECISION_REVIEW, "medium"  # 글자 못읽음/불일치 → 한 단계 강등
    if base_conf == "medium":
        if agree:
            return DECISION_AUTO, "medium"
        return DECISION_REVIEW, "low"
    return DECISION_REVIEW, "low"
