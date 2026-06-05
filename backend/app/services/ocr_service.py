"""OCR 실행 서비스 — 업로드된 증거에 OCR → 엔티티 추출·저장·집계.

로컬: Mock(빈 결과). AWS: Claude Vision / Upstage 하이브리드.
성능: 'done'은 재OCR 안 함(캐싱). 보안: 카톡(chat/other)은 PII 마스킹(계좌·주민번호·전화).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Evidence
from .storage import get_storage

_WORKER = Path(__file__).resolve().parents[3] / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))

log = logging.getLogger("bada")


def _mask_chat(category: str, ocr_text: str, entities: dict):
    """카톡 등 비정형: 제3자 PII(계좌·주민번호·전화) 자동 마스킹(security.md)."""
    if category not in ("chat", "other"):
        return ocr_text, entities
    try:
        from security.pii import mask_pii  # worker
    except Exception:
        return ocr_text, entities
    ocr_text = mask_pii(ocr_text or "")
    for u in (entities.get("utterances") or []):
        if u.get("text"):
            u["text"] = mask_pii(u["text"])
    return ocr_text, entities


def _quality(category: str, ocr_status: str, entities: dict):
    if category in ("chat", "other") and ocr_status == "done":
        try:
            from rules.chat_evidence import assess_chat  # worker
            return assess_chat(entities or {})
        except Exception:
            return None
    return None


def _sanity(ocr_status: str, entities: dict):
    """타당성(모순) 경고 — 통상임금<기본급, 산식 불일치 등."""
    if ocr_status != "done":
        return []
    try:
        from rules.sanity import check_entities  # worker
        return check_entities(entities or {})
    except Exception:
        return []


def _confidence(ocr_status: str, entities: dict, cross: dict | None):
    """근거 기반 필드별 신뢰도(LLM 자기보고 X). cross=증거 간 일치 신호."""
    if ocr_status != "done":
        return None
    try:
        from rules.confidence import assess  # worker
        return assess(entities or {}, cross or {})
    except Exception:
        return None


def _cross_for_case(evs: list[Evidence]) -> dict:
    """증거 간 교차 일치 신호 — 같은 값이 2건 이상에서 일치/불일치하는지(근거 confidence용)."""
    hw = [(e.extracted_entities or {}).get("hourly_wage") for e in evs]
    hw = [x for x in hw if x]
    cross: dict = {}
    if len(hw) >= 2:
        cross["hourly_wage"] = "agree" if len(set(hw)) == 1 else "disagree"
    return cross


def _row(ev: Evidence, cross: dict | None = None):
    ents = ev.extracted_entities or {}
    return {
        "evidence_id": ev.id, "file_name": ev.file_name, "category": ev.category,
        "ocr_status": ev.ocr_status, "ocr_text": (ev.ocr_text or "")[:600],
        "entities": ents, "evidence_quality": _quality(ev.category, ev.ocr_status, ents),
        "sanity": _sanity(ev.ocr_status, ents),
        "confidence": _confidence(ev.ocr_status, ents, cross),
        "error": None,
    }


def _eligible(ev: Evidence) -> bool:
    return ev.file_type in ("image", "pdf") and bool(ev.file_key)


def collect(db: Session, case_id: str) -> dict:
    """OCR을 돌리지 않고 현재 DB 상태로 rows+aggregate를 만든다(폴링용 스냅샷).

    status: 처리 대상 중 하나라도 pending/processing이면 'processing', 아니면 'done'.
    """
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    cross = _cross_for_case(evs)
    targets = [e for e in evs if _eligible(e)]
    rows = [_row(e, cross) for e in targets]
    from services.extract import aggregate  # worker
    agg = aggregate(rows)
    agg["evidences"] = rows
    pending = any(e.ocr_status in ("pending", "processing") for e in targets)
    agg["status"] = "processing" if pending else "done"
    return agg


def mark_processing(db: Session, case_id: str) -> None:
    """비동기 OCR 시작 전, 대상 중 아직 안 끝난(done 아님) 증거를 processing으로 표시(즉시 UI 피드백)."""
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    changed = False
    for ev in evs:
        if _eligible(ev) and ev.ocr_status != "done":
            ev.ocr_status = "processing"
            changed = True
    if changed:
        db.commit()


def update_entities(db: Session, case_id: str, eid: str, entities: dict) -> dict | None:
    """사용자가 OCR 값을 수정(HITL) → 저장. 수정본은 done으로 간주하고 행을 다시 계산."""
    ev = db.get(Evidence, eid)
    if not ev or ev.case_id != case_id:
        return None
    ev.extracted_entities = entities or {}
    ev.ocr_status = "done"
    db.commit()
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    return _row(ev, _cross_for_case(evs))


def run_ocr_on_case(db: Session, case_id: str, force: bool = False) -> dict:
    from providers.ocr import get_ocr      # worker
    from services.extract import aggregate  # worker

    storage = get_storage()
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    collected: list[dict] = []

    for ev in evs:
        if ev.file_type not in ("image", "pdf") or not ev.file_key:
            continue
        if not force and ev.ocr_status == "done":   # 캐싱
            collected.append(ev)
            continue

        ev.ocr_status = "processing"
        err = None
        try:
            data = storage.read(ev.file_key)
            out = get_ocr(ev.category).extract(data, ev.category)
            text, ents = _mask_chat(ev.category, out.get("raw_text", ""), out.get("entities", {}))
            ev.ocr_text = text
            ev.extracted_entities = ents
            ev.ocr_status = "done"
        except Exception as e:
            log.warning("OCR failed for evidence %s: %s", ev.id, e)
            ev.ocr_status = "failed"
            ev.extracted_entities = {}
            err = str(e)[:300]
            ev.ocr_text = f"[OCR 실패] {err}"   # 폴링(GET) 때도 사유가 보이도록 저장
        collected.append((ev, err))

    db.commit()
    # 모든 추출이 끝난 뒤 교차 신호 계산 → 행 생성(근거 confidence 반영)
    cross = _cross_for_case(evs)
    rows = []
    for item in collected:
        if isinstance(item, tuple):
            ev, err = item
            r = _row(ev, cross)
            if err:
                r["error"] = err
            rows.append(r)
        else:
            rows.append(_row(item, cross))

    agg = aggregate(rows)
    agg["evidences"] = rows
    return agg
