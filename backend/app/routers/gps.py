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
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Case, GpsLog, User, Workplace

# 버그#4 수정: worker의 haversine_m을 직접 import해 중복 구현 제거
_WORKER = Path(__file__).resolve().parents[3] / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))
from rules.geofence import haversine_m as _haversine_m  # noqa: E402

router = APIRouter(prefix="/cases/{case_id}/gps", tags=["gps"])


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

    # 버그#2 수정: mocked ping은 status=None으로 저장 (geofence.tag_logs와 일치, domain.md 준수)
    if ping.is_mocked:
        log = GpsLog(case_id=case_id, ts=ping.ts, lat=ping.lat, lng=ping.lng,
                     is_mocked=True, status=None, source=ping.source)
        db.add(log)
        db.commit()
        return {"stored": True, "id": log.id, "status": None,
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

@router.get("/summary", summary="일별 GPS 요약 — Evidence Pack 생성용 (법적 효력 강화판)")
def get_summary(
        case_id: str,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
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

    # 1. 타임존 보정 (UTC → KST 기준 날짜 분리)
    # 버그#1 수정: DB에 저장된 ts가 timezone-naive인 경우 UTC로 간주하고 KST 변환
    # timezone-aware인 경우 utcoffset을 먼저 제거한 뒤 동일하게 처리
    by_date: dict[str, list] = {}
    for l in logs:
        ts = l.ts
        if ts.tzinfo is not None:
            # aware → UTC 기준으로 normalize 후 naive로 변환
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        kst_dt = ts + timedelta(hours=9)
        date_key = kst_dt.strftime("%Y-%m-%d")
        by_date.setdefault(date_key, []).append(l)

    summary = []
    for date_key in sorted(by_date.keys(), reverse=True):
        day_logs = by_date[date_key]

        # 2. IN_WORKPLACE 세션(블록) 분리 알고리즘
        # 버그#3 수정: status가 IN_WORKPLACE가 아닌 모든 값(OUTSIDE, None, UNKNOWN 등)을
        # 명시적으로 구분해 mocked/UNKNOWN 핑이 세그먼트를 잘못 끊지 않도록 처리
        segments = []
        current_segment = []

        for log in day_logs:
            if log.status == "IN_WORKPLACE":
                current_segment.append(log)
            elif log.status == "OUTSIDE":
                # 명확한 이탈 신호 → 현재 블록 저장 후 초기화
                if current_segment:
                    segments.append(current_segment)
                    current_segment = []
            # status가 None(mocked) 또는 UNKNOWN(근무지 미등록)인 경우:
            # 신호로 쓰지 않고 무시 — 세그먼트를 끊지 않음
        if current_segment:
            segments.append(current_segment)

        # 3. 유효 세션 검증 (노이즈 필터링) 및 시간 계산
        valid_blocks = []
        total_minutes = 0

        for seg in segments:
            # 방어 로직: 핑이 딱 1개(연속되지 않음)라면 우연히 지나간 것으로 간주해 폐기
            if len(seg) < 2:
                continue

            seg_start = seg[0].ts
            seg_end = seg[-1].ts
            duration_min = (seg_end - seg_start).total_seconds() / 60

            total_minutes += duration_min
            valid_blocks.append({
                "from_time": seg_start.isoformat(),
                "to_time": seg_end.isoformat(),
                "duration_hours": round(duration_min / 60, 2)
            })

        # 방어 로직: 해당 날짜에 유효한 근무 블록이 하나라도 있을 때만 요약에 추가
        if valid_blocks:
            summary.append({
                "work_date": date_key,
                "first_in": valid_blocks[0]["from_time"],
                # 버그#5 수정: last_in → last_out으로 명칭 변경 (마지막 체류 블록의 마지막 핑 = 퇴근 근사 시각)
                "last_out": valid_blocks[-1]["to_time"],
                "estimated_hours": round(total_minutes / 60, 1),
                "detailed_blocks": valid_blocks  # 점심/외출 시간이 제외된 순수 체류 구간들
            })

    # SHA-256 무결성 해시 (수집 원본 기반)
    raw = [{"id": l.id, "ts": l.ts.isoformat(), "lat": str(l.lat),
            "lng": str(l.lng), "status": l.status} for l in logs]
    data_hash = hashlib.sha256(
        json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()

    return {
        "case_id": case_id,
        "total_days": len(summary),
        "summary": summary,
        "integrity": {
            "sha256": data_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }