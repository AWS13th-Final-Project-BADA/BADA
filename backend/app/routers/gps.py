"""GPS ping 수신 + 지오펜스 판정 + 근무지 등록/조회.

웹/앱이 공유하는 엔드포인트.
- Workplace 등록: POST /cases/{case_id}/gps/workplace
- GPS 핑 수신:    POST /cases/{case_id}/gps/ping  (지오펜스 즉시 판정)
- 로그 조회:      GET  /cases/{case_id}/gps/logs
- 일별 요약:      GET  /cases/{case_id}/gps/summary  (Evidence Pack용)
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Case, GpsLog, User, Workplace

router = APIRouter(prefix="/cases/{case_id}/gps", tags=["gps"])


# ── 헬퍼: Haversine 거리 계산 ─────────────────────────
# PostGIS ST_Distance의 임시 대체. PostgreSQL+PostGIS 전환 시 제거.

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 WGS-84 좌표 간 거리(미터)."""
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_case_or_404(case_id: str, user: User, db: Session) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="사건을 찾을 수 없습니다.")
    return case


# ── 요청 모델 ──────────────────────────────────────────

class WorkplaceIn(BaseModel):
    center_lat: float = Field(..., ge=-90,  le=90,  description="근무지 중심 위도")
    center_lng: float = Field(..., ge=-180, le=180, description="근무지 중심 경도")
    radius_m:   int   = Field(50,  ge=10,  le=500,  description="인정 반경(m)")


class Ping(BaseModel):
    ts:         datetime
    lat:        float = Field(..., ge=-90,  le=90)
    lng:        float = Field(..., ge=-180, le=180)
    is_mocked:  bool  = False
    source:     str   = "web_geo"  # web_geo / app / seed


# ── 엔드포인트 ─────────────────────────────────────────

@router.post("/workplace", summary="근무지(지오펜스) 등록")
def register_workplace(
    case_id: str,
    body:    WorkplaceIn,
    db:      Session = Depends(get_db),
    user:    User    = Depends(get_current_user),
):
    _get_case_or_404(case_id, user, db)

    wp = Workplace(
        case_id    = case_id,
        center_lat = body.center_lat,
        center_lng = body.center_lng,
        radius_m   = body.radius_m,
    )
    db.add(wp)
    db.commit()
    db.refresh(wp)
    return {"id": wp.id, "center_lat": float(wp.center_lat),
            "center_lng": float(wp.center_lng), "radius_m": wp.radius_m}


@router.get("/workplace", summary="등록된 근무지 조회")
def get_workplace(
    case_id: str,
    db:      Session = Depends(get_db),
    user:    User    = Depends(get_current_user),
):
    _get_case_or_404(case_id, user, db)
    wp = db.query(Workplace).filter(Workplace.case_id == case_id).first()
    if not wp:
        raise HTTPException(status_code=404, detail="등록된 근무지가 없습니다.")
    return {"id": wp.id, "center_lat": float(wp.center_lat),
            "center_lng": float(wp.center_lng), "radius_m": wp.radius_m}


@router.post("/ping", summary="GPS 좌표 수신 및 IN/OUT 즉시 판정")
def receive_ping(
    case_id: str,
    ping:    Ping,
    db:      Session = Depends(get_db),
    user:    User    = Depends(get_current_user),
):
    _get_case_or_404(case_id, user, db)

    # Fake GPS → INVALID 기록 후 반환
    if ping.is_mocked:
        log = GpsLog(case_id=case_id, ts=ping.ts, lat=ping.lat, lng=ping.lng,
                     is_mocked=True, status="INVALID", source=ping.source)
        db.add(log)
        db.commit()
        return {"stored": True, "id": log.id, "status": "INVALID",
                "reason": "mock_location_detected"}

    # 지오펜스 판정
    status = "UNKNOWN"
    distance_m = None
    wp = db.query(Workplace).filter(Workplace.case_id == case_id).first()
    if wp:
        distance_m = round(_haversine_m(
            float(wp.center_lat), float(wp.center_lng), ping.lat, ping.lng
        ), 1)
        status = "IN_WORKPLACE" if distance_m <= wp.radius_m else "OUTSIDE"

    log = GpsLog(case_id=case_id, ts=ping.ts, lat=ping.lat, lng=ping.lng,
                 is_mocked=False, status=status, source=ping.source)
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"stored": True, "id": log.id, "status": status, "distance_m": distance_m}


@router.get("/logs", summary="GPS 로그 전체 조회")
def get_logs(
    case_id:        str,
    include_mocked: bool    = False,
    db:             Session = Depends(get_db),
    user:           User    = Depends(get_current_user),
):
    _get_case_or_404(case_id, user, db)
    q = db.query(GpsLog).filter(GpsLog.case_id == case_id)
    if not include_mocked:
        q = q.filter(GpsLog.is_mocked == False)  # noqa: E712
    logs = q.order_by(GpsLog.ts).all()
    return {
        "count": len(logs),
        "logs": [
            {"id": l.id, "ts": l.ts.isoformat(), "lat": float(l.lat),
             "lng": float(l.lng), "status": l.status, "source": l.source}
            for l in logs
        ],
    }


@router.get("/summary", summary="일별 GPS 요약 — Evidence Pack 생성용")
def get_summary(
    case_id: str,
    db:      Session = Depends(get_db),
    user:    User    = Depends(get_current_user),
):
    _get_case_or_404(case_id, user, db)

    logs = (
        db.query(GpsLog)
        .filter(GpsLog.case_id == case_id, GpsLog.is_mocked == False)  # noqa: E712
        .order_by(GpsLog.ts)
        .all()
    )
    if not logs:
        raise HTTPException(status_code=404, detail="GPS 데이터가 없습니다.")

    # 날짜별 그룹핑 (KST UTC+9)
    by_date: dict[str, list] = {}
    for l in logs:
        kst_date = l.ts.strftime("%Y-%m-%d")  # DB가 UTC면 +9 보정 필요
        by_date.setdefault(kst_date, []).append(l)

    summary = []
    for date_key in sorted(by_date.keys(), reverse=True):
        day = by_date[date_key]
        in_logs = [l for l in day if l.status == "IN_WORKPLACE"]
        summary.append({
            "work_date":        date_key,
            "in_count":         len(in_logs),
            "out_count":        len([l for l in day if l.status == "OUTSIDE"]),
            "first_in":         in_logs[0].ts.isoformat()  if in_logs else None,
            "last_in":          in_logs[-1].ts.isoformat() if in_logs else None,
            # 핑 간격 12.5분 기준 체류시간 추정 (참고용)
            "estimated_hours":  round(len(in_logs) * 12.5 / 60, 1),
        })

    # SHA-256 무결성 해시
    raw = [{"id": l.id, "ts": l.ts.isoformat(), "lat": str(l.lat),
            "lng": str(l.lng), "status": l.status} for l in logs]
    data_hash = hashlib.sha256(
        json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()

    return {
        "case_id":    case_id,
        "total_days": len(summary),
        "summary":    summary,
        "integrity":  {
            "sha256":       data_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
