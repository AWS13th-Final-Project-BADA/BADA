"""HITL 엔티티 수정 저장 + 근거 confidence 반환 테스트."""
from app.db import SessionLocal
from app.models import Evidence


def _case_with_evidence(client):
    cid = client.post("/cases", json={"workplace_name": "○○제조",
                                      "issue_types": ["wage_unpaid"]}).json()["id"]
    db = SessionLocal()
    ev = Evidence(case_id=cid, file_key="k1", file_name="명세서.jpg", file_type="image",
                  category="statement", ocr_status="done", ocr_text="명세서",
                  extracted_entities={"hourly_wage": 9000,
                                      "amounts": [{"label": "실지급액", "value": 1800000}]})
    db.add(ev); db.commit(); db.refresh(ev)
    eid = ev.id
    db.close()
    return cid, eid


def test_patch_entities_saves_and_returns_row(client):
    cid, eid = _case_with_evidence(client)
    # 사용자가 시급을 9000 → 10030 으로 수정
    r = client.patch(f"/cases/{cid}/evidences/{eid}/entities",
                     json={"entities": {"hourly_wage": 10030,
                                        "amounts": [{"label": "실지급액", "value": 1800000}]}})
    assert r.status_code == 200
    row = r.json()
    assert row["entities"]["hourly_wage"] == 10030
    assert row["ocr_status"] == "done"
    assert row["confidence"] is not None  # 근거 confidence 포함


def test_patch_unknown_evidence_404(client):
    cid, _ = _case_with_evidence(client)
    r = client.patch(f"/cases/{cid}/evidences/nope/entities", json={"entities": {}})
    assert r.status_code == 404


def test_sanity_flag_lowers_confidence(client):
    cid, eid = _case_with_evidence(client)
    # 통상임금<기본급 모순 입력 → 해당 금액 confidence low
    r = client.patch(f"/cases/{cid}/evidences/{eid}/entities", json={"entities": {
        "amounts": [{"label": "월 통상임금", "value": 2000000},
                    {"label": "기본급", "value": 2100000}]}})
    row = r.json()
    levels = {a["label"]: a["level"] for a in row["confidence"]["amounts"]}
    assert levels["월 통상임금"] == "low"
    assert row["sanity"]  # 모순 경고도 함께
