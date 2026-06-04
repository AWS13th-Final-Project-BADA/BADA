"""분석 실행 서비스 — 규칙 엔진(worker)을 호출해 결과를 만든다.

타임라인·번역대조표 조립은 worker/pipeline + services가 담당(provider 사용).
이 서비스는 ctx를 구성해 넘기고, 결과를 받는다.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# 모노레포 worker 패키지 임포트 경로
_WORKER = Path(__file__).resolve().parents[3] / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))


def _dt(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def run_analysis(case, evidence_categories: set[str], req, target_lang: str = "ko") -> dict:
    """case: ORM Case, req: AnalyzeRequest. 반환: 결과 dict(타임라인·대조표 포함)."""
    from pipeline import process_case  # 경로 세팅 후 지연 임포트

    ctx = {
        "agreed_hourly_wage": case.agreed_hourly_wage,
        "worked_hours": req.worked_hours,
        "deposits": [d.amount for d in req.deposits],
        "deposit_events": [{"date": d.date, "amount": d.amount} for d in req.deposits],
        "raw_deductions": [{"name": d.name, "amount": d.amount} for d in req.deductions],
        "present_categories": evidence_categories,
        "gps_logs": [{"ts": _dt(p.ts), "lat": p.lat, "lng": p.lng, "is_mocked": p.is_mocked} for p in req.gps_logs],
        "workplace": ({"lat": req.workplace.lat, "lng": req.workplace.lng, "radius_m": req.workplace.radius_m}
                      if req.workplace else None),
        "chat_arrivals": [dt for s in req.chat_arrivals if (dt := _dt(s))],
        "work_start_date": str(case.work_start_date) if case.work_start_date else None,
        "workplace_name": case.workplace_name,
        "target_lang": target_lang,
    }
    return process_case(case.id, ctx)
