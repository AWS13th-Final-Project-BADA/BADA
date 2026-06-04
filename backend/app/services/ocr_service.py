"""OCR 실행 서비스 — 업로드된 증거 파일에 OCR을 돌려 엔티티 추출·저장·집계.

로컬(PROVIDER_MODE=local): Mock OCR → 빈 엔티티(키 없으면 추출 없음, 정직).
AWS(PROVIDER_MODE=aws):    Claude Vision / Upstage 하이브리드 실제 호출.

성능: 이미 'done'인 증거는 재OCR하지 않고 저장된 결과를 재사용한다(추출 재클릭이 빠름).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Evidence
from .storage import get_storage

# worker 패키지 임포트 경로
_WORKER = Path(__file__).resolve().parents[3] / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))

log = logging.getLogger("bada")


def _quality(category: str, ocr_status: str, entities: dict):
    if category in ("chat", "other") and ocr_status == "done":
        try:
            from rules.chat_evidence import assess_chat  # worker
            return assess_chat(entities or {})
        except Exception:
            return None
    return None


def run_ocr_on_case(db: Session, case_id: str, force: bool = False) -> dict:
    from providers.ocr import get_ocr      # worker
    from services.extract import aggregate  # worker

    storage = get_storage()
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    collected: list[dict] = []

    for ev in evs:
        if ev.file_type not in ("image", "pdf") or not ev.file_key:
            continue

        # 이미 읽은 건 재사용 (재OCR 안 함) — 속도/비용 절감
        if not force and ev.ocr_status == "done":
            ents = ev.extracted_entities or {}
            collected.append({
                "evidence_id": ev.id, "file_name": ev.file_name, "category": ev.category,
                "ocr_status": "done", "ocr_text": (ev.ocr_text or "")[:600],
                "entities": ents, "evidence_quality": _quality(ev.category, "done", ents), "error": None,
            })
            continue

        ev.ocr_status = "processing"
        error = None
        try:
            data = storage.read(ev.file_key)
            out = get_ocr(ev.category).extract(data, ev.category)
            ev.ocr_text = out.get("raw_text", "")
            ev.extracted_entities = out.get("entities", {})
            ev.ocr_status = "done"
        except Exception as e:  # 실패는 지어내지 않고 failed 표기
            log.warning("OCR failed for evidence %s: %s", ev.id, e)
            ev.ocr_status = "failed"
            ev.extracted_entities = {}
            error = str(e)[:300]

        collected.append({
            "evidence_id": ev.id, "file_name": ev.file_name, "category": ev.category,
            "ocr_status": ev.ocr_status, "ocr_text": (ev.ocr_text or "")[:600],
            "entities": ev.extracted_entities or {},
            "evidence_quality": _quality(ev.category, ev.ocr_status, ev.extracted_entities or {}),
            "error": error,
        })

    db.commit()
    agg = aggregate(collected)
    agg["evidences"] = collected
    return agg
