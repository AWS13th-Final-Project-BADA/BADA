"""핵심 흐름 API 테스트. 기능 담당자는 자기 엔드포인트 테스트를 여기/별도 파일에 추가."""

CASE = {"workplace_name": "○○제조", "work_start_date": "2026-01-15", "work_end_date": "2026-05-31",
        "agreed_hourly_wage": 10320, "agreed_weekly_hours": 40, "issue_types": ["wage_unpaid", "deduction"]}

ANALYZE = {
    "worked_hours": [174, 168, 180, 176],
    "deposits": [{"date": "2026-01-15", "amount": 1500000}, {"date": "2026-02-15", "amount": 1600000},
                 {"date": "2026-03-15", "amount": 1550000}, {"date": "2026-04-15", "amount": 1600000}],
    "deductions": [{"name": "기숙사비", "amount": 250000}, {"name": "식비", "amount": 150000},
                   {"name": "작업복비", "amount": 80000}, {"name": "관리비 명목", "amount": 50000}],
    "workplace": {"lat": 37.5, "lng": 127.0, "radius_m": 50},
    "gps_logs": [{"ts": "2026-01-15T09:05:00", "lat": 37.50003, "lng": 127.00003, "is_mocked": False},
                 {"ts": "2026-01-15T09:00:00", "lat": 37.50003, "lng": 127.00003, "is_mocked": True}],
    "chat_arrivals": ["2026-01-15T09:00:00"],
}


def _make_case(client):
    cid = client.post("/cases", json=CASE).json()["id"]
    for cat in ["contract", "statement", "payment", "chat"]:
        client.post(f"/cases/{cid}/evidences/manual", json={"file_name": cat, "category": cat})
    return cid


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_full_flow(client):
    cid = _make_case(client)
    a = client.post(f"/cases/{cid}/analyze", json=ANALYZE).json()
    assert a["total_expected_wage"] == 7203360
    assert a["suspected_unpaid"] == 953360
    assert [d["category"] for d in a["deduction_items"]] == ["기숙사비", "식비", "작업복/장비", "기타공제"]
    assert a["gps"]["cross_matches"] == 1
    assert len(a["timeline"]) >= 3
    assert len(a["translation_pairs"]) >= 4


def test_persistence_endpoints(client):
    cid = _make_case(client)
    client.post(f"/cases/{cid}/analyze", json=ANALYZE)
    assert client.get(f"/cases/{cid}/analysis").json()["suspected_unpaid"] == 953360
    assert len(client.get(f"/cases/{cid}/timeline").json()) >= 3
    assert len(client.get(f"/cases/{cid}/translation-pairs").json()) >= 4
    assert client.get(f"/cases/{cid}/report.html").status_code == 200


def test_missing_when_no_evidence(client):
    cid = client.post("/cases", json=CASE).json()["id"]
    a = client.post(f"/cases/{cid}/analyze", json=ANALYZE).json()
    items = {m["item"] for m in a["missing_evidences"]}
    assert {"payment", "schedule", "contract", "chat"} <= items


def test_extract_local_mock_empty(client):
    """로컬(목) 모드: 파일 OCR 추출이 빈 결과여야 함(키 없으면 추출 없음)."""
    cid = _make_case(client)  # manual 증거는 파일 없음 → 추출 대상 아님
    r = client.post(f"/cases/{cid}/evidences/extract").json()
    assert r["worked_hours"] == []
    assert r["deposits"] == []
    assert "needs_review" in r
