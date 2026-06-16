"""비동기 /extract — 킥(POST) + 폴링(GET) + 동기(wait) 경로."""

CASE = {"workplace_name": "○○제조", "issue_types": ["wage_unpaid"]}


def _case(client):
    return client.post("/cases", json=CASE).json()["id"]


def test_extract_default_async_returns_status(client):
    """기본 POST는 상태 스냅샷 반환. 파일이 없으면 처리할 게 없어 즉시 done."""
    cid = _case(client)
    r = client.post(f"/cases/{cid}/evidences/extract").json()
    assert r["status"] == "done"
    assert r["evidences"] == []
    assert "needs_review" in r


def test_extract_status_poll_endpoint(client):
    """GET 폴링 엔드포인트가 현재 상태를 돌려준다."""
    cid = _case(client)
    r = client.get(f"/cases/{cid}/evidences/extract").json()
    assert r["status"] == "done"
    assert r["evidences"] == []


def test_extract_wait_true_is_sync(client):
    """wait=true는 OCR을 끝까지 돌려 집계 결과를 동기 반환(테스트·간단 케이스)."""
    cid = _case(client)
    r = client.post(f"/cases/{cid}/evidences/extract?wait=true").json()
    assert r["worked_hours"] == []
    assert r["deposits"] == []
    assert "needs_review" in r
