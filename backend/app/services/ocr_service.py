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


def _row(ev: Evidence):
    ents = ev.extracted_entities or {}
    return {
        "evidence_id": ev.id, "file_name": ev.file_name, "category": ev.category,
        "ocr_status": ev.ocr_status, "ocr_text": (ev.ocr_text or "")[:600],
        "entities": ents, "evidence_quality": _quality(ev.category, ev.ocr_status, ents),
        "sanity": _sanity(ev.ocr_status, ents),
        "error": None,
    }


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
            collected.append(_row(ev))
            continue

        ev.ocr_status = "processing"
        row = None
        try:
            data = storage.read(ev.file_key)
            out = get_ocr(ev.category).extract(data, ev.category)
            text, ents = _mask_chat(ev.category, out.get("raw_text", ""), out.get("entities", {}))
            ev.ocr_text = text
            ev.extracted_entities = ents
            ev.ocr_status = "done"