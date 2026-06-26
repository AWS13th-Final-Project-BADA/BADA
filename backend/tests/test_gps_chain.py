"""GPS chain_hash 무결성 검증 테스트.

1. 핑 여러 개 전송 → /verify 체인 정상 확인
2. DB 직접 조작 → /verify 체인 손상 탐지 확인
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone


# ── 헬퍼 (gps.py의 _compute_chain_hash와 동일 로직) ──
def _compute_chain_hash(prev_hash, ts, lat, lng, status):
    payload = "|".join([
        prev_hash or "",
        ts.isoformat(),
        f"{lat:.7f}",
        f"{lng:.7f}",
        status or "",
    ])
    return hashlib.sha256(payload.encode()).hexdigest()


def _create_case(client) -> str:
    r = client.post("/cases", json={
        "workplace_name": "테스트공장",
        "work_start_date": "2026-01-01",
        "agreed_hourly_wage": 10000,
        "agreed_weekly_hours": 40,
        "issue_types": [],
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _register_workplace(client, case_id: str):
    r = client.post(f"/cases/{case_id}/gps/workplace", json={
        "center_lat": 37.5,
        "center_lng": 127.0,
        "radius_m": 100,
    })
    assert r.status_code == 200, r.text


def _ping(client, case_id: str, lat: float, lng: float, ts: str):
    r = client.post(f"/cases/{case_id}/gps/ping", json={
        "ts": ts,
        "lat": lat,
        "lng": lng,
        "is_mocked": False,
        "source": "web_geo",
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_chain_intact_after_multiple_pings(client):
    """핑 3개 전송 후 /verify → chain_intact=True."""
    case_id = _create_case(client)
    _register_workplace(client, case_id)

    for i in range(3):
        _ping(client, case_id, 37.5, 127.0, f"2026-06-01T0{i}:00:00+00:00")

    r = client.get(f"/cases/{case_id}/gps/verify")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["chain_intact"] is True
    assert data["broken_count"] == 0
    assert data["total_logs"] == 3


def test_chain_broken_after_db_tampering(client):
    """핑 2개 전송 후 첫 번째 로그의 lat을 직접 수정 → /verify → chain_intact=False."""
    import os
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"

    from app.db import SessionLocal
    from app.models import GpsLog

    case_id = _create_case(client)
    _register_workplace(client, case_id)

    _ping(client, case_id, 37.5, 127.0, "2026-06-01T01:00:00+00:00")
    _ping(client, case_id, 37.5, 127.0, "2026-06-01T02:00:00+00:00")

    # DB 직접 조작: 첫 번째 핑의 lat 변경 (hash는 그대로 두어 불일치 유발)
    db = SessionLocal()
    try:
        first = db.query(GpsLog).filter(GpsLog.case_id == case_id).order_by(GpsLog.ts).first()
        first.lat = 99.9999  # 전혀 다른 좌표로 조작
        db.commit()
    finally:
        db.close()

    r = client.get(f"/cases/{case_id}/gps/verify")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["chain_intact"] is False
    assert data["broken_count"] >= 1
