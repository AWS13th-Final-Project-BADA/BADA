"""GPS 지오펜스 + 카톡 교차검증 — 규칙 기반(domain.md). LLM 사용 금지.

운영 DB에서는 PostGIS ST_Contains/ST_DWithin 사용. 아래는 동일 의미의 순수 파이썬 구현
(단위테스트 + 로컬 개발용). is_mocked=True 핑은 모두 배제한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
    """logs: [{"ts": datetime, "lat","lng","is_mocked"(opt),"is_delayed_upload"(opt)}].
    is_mocked=True 또는 is_delayed_upload=True 핑은 excluded=True로 배제한다.
    is_delayed_upload 핑은 타임라인·교차검증에서 제외하되 기록은 보존한다.
    """
    out = []
    for lg in logs:
        if lg.get("is_mocked"):
            out.append({**lg, "status": None, "excluded": True, "exclude_reason": "mocked"})
            continue
        if lg.get("is_delayed_upload"):
            out.append({**lg, "status": None, "excluded": True, "exclude_reason": "delayed_upload"})
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


# KST(UTC+9). gps.py와 동일 — 자정 근처 핑이 전날로 기록되는 문제 방지.
_KST = timezone(timedelta(hours=9))


def _kst_date(ts: datetime) -> str:
    t = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return t.astimezone(_KST).strftime("%Y-%m-%d")


def summarize_by_day(tagged_logs: list[dict], max_gap_min: int = 30) -> list[dict]:
    """tag_logs() 결과를 일(Day) 단위로 요약 — Evidence Pack용 (규칙 기반).

    배제된 핑(mocked/delayed)은 집계에서 제외한다.
    체류시간은 IN_WORKPLACE 핑 간 실제 간격을 합산하되,
    간격이 max_gap_min(기본 30분)을 넘으면 연속으로 보지 않는다(핑 끊김 구간 배제).

    반환: [{"work_date","in_count","out_count","first_in","last_out","estimated_hours","hours_method"}]
    날짜 내림차순 정렬.
    """
    by_date: dict[str, list[dict]] = {}
    for lg in tagged_logs:
        if lg.get("excluded"):
            continue
        ts = lg.get("ts")
        if not isinstance(ts, datetime):
            continue
        by_date.setdefault(_kst_date(ts), []).append(lg)

    summary: list[dict] = []
    for date_key in sorted(by_date.keys(), reverse=True):
        day = by_date[date_key]
        in_logs = sorted(
            [l for l in day if l.get("status") == "IN_WORKPLACE"],
            key=lambda l: l["ts"],
        )
        total_in_sec = 0.0
        for i in range(1, len(in_logs)):
            gap = (in_logs[i]["ts"] - in_logs[i - 1]["ts"]).total_seconds()
            if gap <= max_gap_min * 60:
                total_in_sec += gap
        summary.append({
            "work_date":       date_key,
            "in_count":        len(in_logs),
            "out_count":       sum(1 for l in day if l.get("status") == "OUTSIDE"),
            "first_in":        _kst_date_time(in_logs[0]["ts"]) if in_logs else None,
            "last_out":        _kst_date_time(in_logs[-1]["ts"]) if in_logs else None,
            "estimated_hours": round(total_in_sec / 3600, 1),
            "hours_method":    "actual_intervals" if len(in_logs) > 1 else "insufficient_pings",
        })
    return summary


def _kst_date_time(ts: datetime) -> str:
    t = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return t.astimezone(_KST).strftime("%Y-%m-%d %H:%M")
