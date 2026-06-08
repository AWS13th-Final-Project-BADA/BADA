from datetime import datetime

from rules.geofence import cross_check, haversine_m, tag_logs, tag_ping

# 근무지 중심 (예: 서울 어딘가)
CENTER = (37.5000, 127.0000)


def test_haversine_known_distance():
    # 위도 0.001도 ≈ 111m
    d = haversine_m(37.5000, 127.0, 37.5010, 127.0)
    assert 100 < d < 120


def test_tag_in_and_out():
    assert tag_ping(37.50003, 127.00003, *CENTER, radius_m=50) == "IN_WORKPLACE"
    assert tag_ping(37.5030, 127.0030, *CENTER, radius_m=50) == "OUTSIDE"


def test_mocked_pings_excluded():
    logs = [
        {"ts": datetime(2026, 1, 15, 9, 0), "lat": 37.50003, "lng": 127.00003},
        {"ts": datetime(2026, 1, 15, 9, 0), "lat": 37.50003, "lng": 127.00003, "is_mocked": True},
    ]
    tagged = tag_logs(logs, *CENTER, radius_m=50)
    assert tagged[0]["status"] == "IN_WORKPLACE" and tagged[0]["excluded"] is False
    assert tagged[1]["status"] is None and tagged[1]["excluded"] is True


def test_cross_check_matches_chat_arrival():
    logs = [{"ts": datetime(2026, 1, 15, 9, 5), "lat": 37.50003, "lng": 127.00003}]
    tagged = tag_logs(logs, *CENTER, radius_m=50)
    matches = cross_check(tagged, [datetime(2026, 1, 15, 9, 0)], window_min=30)
    assert len(matches) == 1 and matches[0]["match"] is True

    # 버그#6 수정 반영: 시간대가 멀면 match=False로 반환됨 (빈 리스트가 아님)
    no_match = cross_check(tagged, [datetime(2026, 1, 15, 12, 0)], window_min=30)
    assert len(no_match) == 1
    assert no_match[0]["match"] is False
    assert no_match[0]["gps_ts"] is None
