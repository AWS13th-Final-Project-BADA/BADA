"""GPS 지오펜스 + 카톡 교차검증 — 규칙 기반(domain.md). LLM 사용 금지.

운영 DB에서는 PostGIS ST_Contains/ST_DWithin 사용. 아래는 동일 의미의 순수 파이썬 구현
(단위테스트 + 로컬 개발용). is_mocked=True 핑은 모두 배제한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def tag_ping(lat: float, lng: float, center_lat: float, center_lng: float, radius_m: float = 50) -> str:
    """근무지 반경 안이면 IN_WORKPLACE, 밖이면 OUTSIDE."""
    return "IN_WORKPLACE" if haversine_m(lat, lng, center_lat, center_lng) <= radius_m else "OUTSIDE"


def tag_logs(logs: list[dict], center_lat: float, center_lng: float, radius_m: float = 50) -> list[dict]:
    """logs: [{"ts": datetime, "lat","lng","is_mocked"(opt)}]. is_mocked는 status=None으로 배제."""
    out = []
    for lg in logs:
        if lg.get("is_mocked"):
            out.append({**lg, "status": None, "excluded": True})
            continue
        status = tag_ping(lg["lat"], lg["lng"], center_lat, center_lng, radius_m)
        out.append({**lg, "status": status, "excluded": False})
    return out


def cross_check(
    tagged_logs: list[dict],
    chat_arrivals: list[datetime],
    window_min: int = 30,
) -> list[dict]:
    """같은 시간대(±window_min)에 '도착' 카톡 발화와 IN_WORKPLACE 핑이 함께 있으면 정황 일치.

    반환: [{"chat_ts": datetime, "gps_ts": datetime|None, "match": bool}]
    - match=True : 창 안에 IN_WORKPLACE 핑이 존재 → 정황 일치
    - match=False: 창 안에 IN_WORKPLACE 핑 없음 → 정황 불일치 (도착 발화만 존재)
    교차검증은 시간 매칭 규칙이며 위법을 판단하지 않는다.
    """
    in_pings = [lg for lg in tagged_logs if not lg.get("excluded") and lg.get("status") == "IN_WORKPLACE"]
    results: list[dict] = []
    win = timedelta(minutes=window_min)
    for chat_ts in chat_arrivals:
        nearest = None
        for p in in_pings:
            if abs(p["ts"] - chat_ts) <= win:
                if nearest is None or abs(p["ts"] - chat_ts) < abs(nearest["ts"] - chat_ts):
                    nearest = p
        if nearest is not None:
            results.append({"chat_ts": chat_ts, "gps_ts": nearest["ts"], "match": True})
        else:
            # 버그#6 수정: 매칭 실패 케이스도 반환해 "정황 불일치" 추적 가능하게 함
            results.append({"chat_ts": chat_ts, "gps_ts": None, "match": False})
    return results
