"""증거 수집 에이전트 API 통합 테스트 (로컬 mock 모드).

목적(가상환경 #1): AWS 없이 /scan, /assess, /agent-upload 엔드포인트가
well-formed 응답을 주고, HITL 불변식을 지키는지 검증한다.

HITL 불변식:
  - /scan 은 후보를 추천만 한다 → DB에 증거를 등록하지 않는다.
  - /agent-upload 만 DB에 등록한다(category="auto", ocr_status="pending").
  - 로컬 mock 분류라 내용 미확인 → 자동 확정(auto_accept) 없음, 전부 needs_review.
"""

CASE = {
    "workplace_name": "○○제조", "work_start_date": "2026-01-15",
    "work_end_date": "2026-05-31", "agreed_hourly_wage": 10320,
    "agreed_weekly_hours": 40, "issue_types": ["wage_unpaid"],
}


def _make_case(client):
    return client.post("/cases", json=CASE).json()["id"]


def _img(name):
    # 내용은 중요치 않음(로컬 mock 분류) — 멀티파트 형식만 맞추면 됨
    return ("files", (name, b"\xff\xd8\xff\x00fake-jpeg", "image/jpeg"))


def test_scan_returns_well_formed_candidates(client):
    cid = _make_case(client)
    r = client.post(
        f"/cases/{cid}/evidences/scan",
        files=[_img("a.jpg"), _img("b.png"), _img("c.jpg")],
    )
    assert r.status_code == 200
    body = r.json()
    assert {"candidates", "summary", "recommended"} <= body.keys()
    assert len(body["candidates"]) == 3
    # 각 후보는 사람이 검토할 수 있는 설명 필드를 갖춘다
    for c in body["candidates"]:
        assert {"file_name", "category", "decision", "confidence", "reasons"} <= c.keys()
    # 로컬 mock: 내용 미확인 → 자동 확정 없음
    assert body["summary"].get("auto_accept", 0) == 0
    # summary 합 == 입력 수
    assert sum(body["summary"].values()) == 3


def test_scan_does_not_register_evidence_hitl(client):
    """스캔은 추천만 — DB에 증거를 만들면 안 된다(HITL)."""
    cid = _make_case(client)
    client.post(f"/cases/{cid}/evidences/scan", files=[_img("a.jpg"), _img("b.jpg")])
    listed = client.get(f"/cases/{cid}/evidences").json()
    assert listed == []  # 등록된 증거 없음


def test_assess_one_returns_decision_fields(client):
    cid = _make_case(client)
    # /assess 는 단일 파일(field='file')
    r = client.post(
        f"/cases/{cid}/evidences/assess",
        files={"file": ("payslip.jpg", b"\xff\xd8\xff\x00fake-jpeg", "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["file_name"] == "payslip.jpg"
    assert {"suggested_category", "decision", "confidence", "reasons"} <= body.keys()
    # 로컬 mock 분류는 보류값 → 자동 확정이 아니라 검토 필요
    assert body["decision"] in ("needs_review", "rejected")


def test_agent_upload_registers_as_auto_pending(client):
    """승인된 파일만 agent-upload로 등록 → category=auto, ocr_status=pending."""
    cid = _make_case(client)
    r = client.post(
        f"/cases/{cid}/evidences/agent-upload",
        files=[_img("a.jpg"), _img("b.jpg")],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["uploaded"] == 2
    assert "extract" in body["next_step"]

    listed = client.get(f"/cases/{cid}/evidences").json()
    assert len(listed) == 2
    for ev in listed:
        assert ev["category"] == "auto"
        assert ev["ocr_status"] == "pending"


def test_scan_then_upload_full_flow(client):
    """스캔(추천) → 승인 가정 → agent-upload(등록) 순서가 끊김 없이 이어진다."""
    cid = _make_case(client)
    scan = client.post(
        f"/cases/{cid}/evidences/scan",
        files=[_img("a.jpg"), _img("b.jpg")],
    ).json()
    # 추천 후보를 '사용자가 승인했다'고 가정하고 그대로 업로드
    approved = scan["recommended"]
    assert set(approved) == {"a.jpg", "b.jpg"}

    up = client.post(
        f"/cases/{cid}/evidences/agent-upload",
        files=[_img(name) for name in approved],
    ).json()
    assert up["uploaded"] == len(approved)
    assert len(client.get(f"/cases/{cid}/evidences").json()) == len(approved)
