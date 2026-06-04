"""분석 실행 서비스 — 저장된 OCR 엔티티 + (선택)수동 입력으로 ctx를 구성해 규칙 엔진 호출.

OCR이 끝난 사건이면 사용자가 숫자를 안 넣어도 분석이 된다(추출값 자동 사용).
수동 입력(req)이 있으면 그 값이 우선(override).
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Evidence

_WORKER = Path(__file__).resolve().parents[3] / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))


def _dt(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def run_analysis(db: Session, case, req, target_lang: str = "ko") -> dict:
    from pipeline import process_case        # worker
    from services.extract import aggregate   # worker

    evs = db.query(Evidence).filter(Evidence.case_id == case.id).all()
    present = {e.category for e in evs}

    # --- OCR 추출값 집계 ---
    collected = [{"category": e.category, "entities": e.extracted_entities or {}}
                 for e in evs if e.extracted_entities]
    ocr = aggregate(collected)
    evidence_entities = collected  # compare용

    # 카톡 발화 → 타임라인 입력
    chat_utts = []
    for e in evs:
        if e.category in ("chat", "other") and e.extracted_entities:
            ents = e.extracted_entities
            date = (ents.get("dates") or [None])[0]
            for u in ents.get("utterances", []) or []:
                chat_utts.append({
                    "date": date, "speaker": u.get("speaker"), "text": u.get("text"),
                    "kind": u.get("kind"), "confidence": u.get("confidence", "low"),
                    "source_evidence_id": e.id,
                })

    # --- 수동 입력(req) 우선, 없으면 OCR 추출값 ---
    worked_hours = req.worked_hours or ocr.get("worked_hours") or []
    deposits = ([{"date": d.date, "amount": d.amount} for d in req.deposits]
                if req.deposits else ocr.get("deposits") or [])
    deductions = ([{"name": d.name, "amount": d.amount} for d in req.deductions]
                  if req.deductions else ocr.get("deductions") or [])
    hourly = req.agreed_hourly_wage or case.agreed_hourly_wage or ocr.get("agreed_hourly_wage")

    ctx = {
        "agreed_hourly_wage": hourly,
        "worked_hours": worked_hours,
        "deposits": [d["amount"] for d in deposits],
        "deposit_events": deposits,
        "raw_deductions": deductions,
        "present_categories": present,
        "evidence_entities": evidence_entities,
        "chat_utterances": chat_utts,
        "gps_logs": [{"ts": _dt(p.ts), "lat": p.lat, "lng": p.lng, "is_mocked": p.is_mocked} for p in req.gps_logs],
        "workplace": ({"lat": req.workplace.lat, "lng": req.workplace.lng, "radius_m": req.workplace.radius_m}
                      if req.workplace else None),
        "chat_arrivals": [dt for s in req.chat_arrivals if (dt := _dt(s))],
        "work_start_date": str(case.work_start_date) if case.work_start_date else None,
        "workplace_name": case.workplace_name or ocr.get("workplace_name"),
        "target_lang": target_lang,
    }
    return p