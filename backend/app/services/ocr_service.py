"""OCR 실행 서비스 — 업로드된 증거 파일에 OCR을 돌려 엔티티 추출·저장·집계.

로컬(PROVIDER_MODE=local): Mock OCR → 빈 엔티티(키 없으면 추출 없음, 정직).
AWS(PROVIDER_MODE=aws):    Claude Vision / Upstage 하이브리드 실제 호출.
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


def run_ocr_on_case(db: Session, case_id: str) -> dict:
    from providers.ocr import get_ocr      # worker
    from services.extract import aggregate  # worker

    storage = get_storage()
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    collected: list[dict] = []

    for ev in evs:
        if ev.file_type not in ("image", "pdf") or not ev.file_key:
            continue
        ev.ocr_status = "processing"
        try:
            data = storage.read(ev.file_key)
            out = get_ocr(ev.category).extract(data, ev.category)
            ev.ocr_text = out.get("raw_text", "")
            ev.extracted_entities = out.get("entities", {})
            ev.ocr_status = "done"
        except Exception as e:  # 호출 실패/검증 실패 → 지어내지 않고 failed 표기
            log.warning("OCR failed for evidence %s: %s", ev.id, e)
            ev.ocr_status = "failed"
            ev.extracted_entities = {}
        collected.append({"category": ev.category, "entities": ev.extracted_entities or {},
                          "evidence_id": ev.id, "ocr_status": ev.ocr_status})

    db.commit()
    agg = aggregate(collected)
    agg["evidences"] = collected
    return agg
