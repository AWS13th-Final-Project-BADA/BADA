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
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Case, GpsLog, User, Workplace

# 기기 시각과 서버 수신 시각의 허용 오차(초).
# 이 값을 초과하면 is_delayed_upload=True → Evidence Pack에 "지연 업로드" 표기.
DELAYED_THRESHOLD_SEC = 60

KST = ZoneInfo("Asia/Seoul")

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


# ── 헬퍼: 무결성 체인 해시 계산 ───────────────────────
# SHA-256(prev_hash | ts_iso | lat | lng | status)
# prev_chain_hash가 없는 첫 번째 핑은 prev를 "" 으로 처리.
# 체인이 연결되어 있으면 DB 직접 수정 시 이후 행의 해시가 전부 깨져 탐지 가능.

def _compute_chain_hash(
    prev_hash: str | None,
    ts: datetime,
    lat: float,
    lng: float,
    status: str | None,
) -> str:
    payload = "|".join([
        prev_hash or "",
        ts.isoformat(),
        f"{lat:.7f}",
        f"{lng:.7f}",
        status or "",
    ])
    return hashlib.sha256(payload.encode()).hexdigest()


def _get_last_chain_hash(case_id: str, db: Session) -> str | None:
    """해당 사건의 가장 최근 GPS 로그 chain_hash를 반환 (체인 연결용)."""
    last = (
        db.query(GpsLog)
        .filter(GpsLog.case_id == case_id)
        .order_by(GpsLog.server_ts.desc())
        .first()
    )
    return last.chain_hash if last else None


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

    # 서버 수신 시각과 기기 시각의 차이로 지연 업로드 탐지
    server_now = datetime.now(timezone.utc)
    # ping.ts가 timezone-naive이면 UTC로 간주
    ping_ts = ping.ts if ping.ts.tzinfo else ping.ts.replace(tzinfo=timezone.utc)
    delay_sec = abs((server_now - ping_ts).total_seconds())
    is_delayed = delay_sec > DELAYED_THRESHOLD_SEC

    # 버그#2 수정: mocked ping은 status=None으로 저장 (geofence.tag_logs와 일치, domain.md 준수)
    if ping.is_mocked:
        prev_hash = _get_last_chain_hash(case_id, db)
        chain_hash = _compute_chain_hash(prev_hash, ping_ts, ping.lat, ping.lng, None)
        log = GpsLog(
            case_id=case_id, ts=ping_ts, lat=ping.lat, lng=ping.lng,
            is_mocked=True, status=None, source=ping.source,
            is_delayed_upload=is_delayed,
            prev_chain_hash=prev_hash,
            chain_hash=chain_hash,
        )
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

    # 무결성 체인 계산 (이전 행의 hash를 이어받아 연결)
    prev_hash = _get_last_chain_hash(case_id, db)
    chain_hash = _compute_chain_hash(prev_hash, ping_ts, ping.lat, ping.lng, status)

    log = GpsLog(
        case_id=case_id, ts=ping_ts, lat=ping.lat, lng=ping.lng,
        is_mocked=False, status=status, source=ping.source,
        is_delayed_upload=is_delayed,
        prev_chain_hash=prev_hash,
        chain_hash=chain_hash,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    response: dict = {
        "stored": True, "id": log.id, "status": status, "distance_m": distance_m,
    }
    # 지연 업로드 경고: Evidence Pack 생성 시 해당 핑에 "지연 업로드" 배지 부착
    if is_delayed:
        response["warning"] = f"delayed_upload ({int(delay_sec)}s)"
    return response


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

    # 날짜별 그룹핑 — UTC → KST(UTC+9) 변환 후 날짜 추출
    # 미보정 시 자정(00:00~08:59) 핑이 전날 날짜로 기록되어
    # 급여명세서·카톡 등 타 증거와 날짜 불일치 발생 (버그#1 수정).
    by_date: dict[str, list] = {}
    for l in logs:
        ts_utc = l.ts if l.ts.tzinfo else l.ts.replace(tzinfo=timezone.utc)
        kst_date = ts_utc.astimezone(KST).strftime("%Y-%m-%d")
        by_date.setdefault(kst_date, []).append(l)

    summary = []
    for date_key in sorted(by_date.keys(), reverse=True):
        day = by_date[date_key]
        # 버그#3 수정: IN_WORKPLACE만 명시적으로 필터 — UNKNOWN/None 핑이 세그먼트를 끊지 않음
        in_logs = [l for l in day if l.status == "IN_WORKPLACE"]
        delayed_count = sum(1 for l in day if l.is_delayed_upload)

        # 체류시간: 실제 핑 간격 합산
        # 핑 간격이 MAX_GAP_MIN(30분) 초과이면 연속으로 보지 않음
        # (중간에 앱 종료·터널 등으로 핑이 끊긴 구간은 체류로 산입하지 않음)
        MAX_GAP_MIN = 30
        total_in_sec = 0.0
        for i in range(1, len(in_logs)):
            prev_ts = in_logs[i - 1].ts if in_logs[i - 1].ts.tzinfo else in_logs[i - 1].ts.replace(tzinfo=timezone.utc)
            curr_ts = in_logs[i].ts     if in_logs[i].ts.tzinfo     else in_logs[i].ts.replace(tzinfo=timezone.utc)
            gap_sec = (curr_ts - prev_ts).total_seconds()
            if gap_sec <= MAX_GAP_MIN * 60:
                total_in_sec += gap_sec
        estimated_hours = round(total_in_sec / 3600, 1)

        entry: dict = {
            "work_date":       date_key,
            "in_count":        len(in_logs),
            "out_count":       len([l for l in day if l.status == "OUTSIDE"]),
            "first_in":        in_logs[0].ts.astimezone(KST).isoformat() if in_logs else None,
            # 버그#5 수정: last_in → last_out으로 명칭 변경 (마지막 체류 핑 = 퇴근 근사 시각)
            "last_out":        in_logs[-1].ts.astimezone(KST).isoformat() if in_logs else None,
            "estimated_hours": estimated_hours,
            "hours_method":    "actual_intervals" if len(in_logs) > 1 else "insufficient_pings",
        }
        # 지연 업로드 핑이 있으면 Evidence Pack에 경고 플래그 포함
        if delayed_count:
            entry["delayed_pings"] = delayed_count
            entry["delayed_warning"] = (
                f"{delayed_count}건의 핑이 기기 시각과 서버 수신 시각이 "
                f"{DELAYED_THRESHOLD_SEC}초 이상 차이납니다. 상담 시 확인이 필요합니다."
            )
        summary.append(entry)

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
        }
    }
