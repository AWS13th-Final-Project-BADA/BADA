"""GPS ping 수신 — 웹/앱이 공유하는 엔드포인트. 지오펜스 판정은 워커/규칙엔진이."""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import GpsLog

router = APIRouter(prefix="/cases/{case_id}/gps", tags=["gps"])


class Ping(BaseModel):
    ts: datetime
    lat: float
    lng: float
    is_mocked: bool = False
    source: str = "web_geo"  # web_geo/app/seed


@router.post("/ping")
def receive_ping(case_id: str, ping: Ping, db: Session = Depends(get_db)):
    # status 태깅은 분석 단계에서 규칙엔진(geofence)이 채운다.
    log = GpsLog(case_id=case_id, ts=ping.ts, lat=ping.lat, lng=ping.lng,
                 is_mocked=ping.is_mocked, source=ping.source)
    db.add(log)
    db.commit()
    return {"stored": True, "id": log.id}
