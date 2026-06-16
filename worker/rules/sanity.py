"""타당성(말이 되는 값인가) 검사 — 규칙 기반. OCR 오류(특히 손글씨)를 객관적으로 잡는다.

OCR 두 번 돌리지 않고도 '모순된 값'을 잡아내는 무료 검증 레이어(docs/ocr-roadmap.md).
예: 월 통상임금 < 기본급(손글씨 혼동), 실지급액 > 지급총액, 지급계-공제계 ≠ 실지급액.
결과는 '확정'이 아니라 '확인 필요' 안내(product.md).
"""
from __future__ import annotations


def _amt(entities: dict, *keys: str):
    """amounts[]에서 label에 keys가 포함된 정수 값을 찾는다."""
    for a in entities.get("amounts", []) or []:
        label = a.get("label") or ""
        if any(k in label for k in keys):
            v = a.get("value")
            if isinstance(v, int):
                return v
    return None


def check_entities(entities: dict) -> list[dict]:
    """단일 문서 엔티티의 모순 검사. 반환: [{field, note, level}]."""
    out: list[dict] = []
    통상 = _amt(entities, "통상임금")
    기본 = _amt(entities, "기본급")
    지급계 = _amt(entities, "지급액 계", "지급액계", "지급총액", "지급 총액")
    공제계 = _amt(entities, "공제액 계", "공제액계", "공제총액", "공제 총액")
    실지급 = _amt(entities, "실지급")

    if 통상 is not None and 기본 is not None and 통상 < 기본:
        out.append({"field": "통상임금/기본급", "level": "high",
                    "note": f"월 통상임금({통상:,}원)이 기본급({기본:,}원)보다 작습니다. 손글씨 인식 오류일 수 있어요 — 확인 필요."})
    if 지급계 is not None and 실지급 is not None and 실지급 > 지급계:
        out.append({"field": "실지급액", "level": "high",
                    "note": f"실지급액({실지급:,}원)이 지급총액({지급계:,}원)보다 큽니다 — 확인 필요."})
    if None not in (지급계, 공제계, 실지급) and (지급계 - 공제계) != 실지급:
        out.append({"field": "명세서 산식", "level": "medium",
                    "note": f"지급계({지급계:,}) − 공제계({공제계:,}) ≠ 실지급({실지급:,}). 숫자 확인이 필요해요."})
    return out


def check_all(evidence_entities: list[dict]) -> list[dict]:
    """여러 문서 전체 검사."""
    out: list[dict] = []
    for ev in evidence_entities:
        out.extend(check_entities(ev.get("entities") or {}))
    return out
