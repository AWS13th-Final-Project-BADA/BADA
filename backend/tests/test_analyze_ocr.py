"""저장된 OCR 엔티티로 분석이 되는지 (요약·타임라인·검증포인트)."""
from app.db import SessionLocal
from app.models import Case, Evidence, User


def _seed(client):
    """명세서·통장·카톡 엔티티를 가진 사건을 DB에 직접 심는다."""
    cid = client.post("/cases", json={"workplace_name": "○○제조", "work_start_date": "2026-01-15",
                                      "agreed_hourly_wage": 10350, "issue_types": ["wage_unpaid"]}).json()["id"]
    db = SessionLocal()
    db.add(Evidence(case_id=cid, file_key="k1", file_name="명세서.pdf", file_type="pdf",
                    category="statement", ocr_status="done", ocr_text="급여명세서",
                    extracted_entities={"hourly_wage": 10350, "amounts": [{"label": "실지급액", "value": 186300}]}))
    db.add(Evidence(case_id=cid, file_key="k2", file_name="통장.jpg", file_type="image",
                    category="payment", ocr_status="done", ocr_text="입금",
                    extracted_entities={"amounts": [{"label": "입금", "value": 150000}]}))
    db.add(Evidence(case_id=cid, file_key="k3", file_name="카톡.jpg", file_type="image",
                    category="chat", ocr_status="done", ocr_text="대화",
                    extracted_entities={"dates": ["2019-11"], "utterances": [
                        {"speaker": "사업주", "text": "마지막 한달 급여 입금처리할게", "kind": "wage_promise"}]}))
    db.commit()
    db.close()
    return cid


def test_analyze_uses_ocr_entities(client):
    cid = _seed(client)
    a = client.post(f"/cases/{cid}/analyze", json={}).json()  # 빈 body → OCR 자동 사용
    assert a["schema_version"] == "1.0"
    # 검증포인트: 명세서 실지급 186300 vs 통장 150000 → 차이
    cmp = {c["key"]: c for c in a["comparisons"]}
    assert cmp["net_vs_deposit"]["status"] == "mismatch"
    assert cmp["net_vs_deposit"]["values"]["차액"] == 36300
    # 카톡 발화 → 타임라인(확인 필요 + 출처)
    chat = [e for e in a["timeline"] if e["type"] == "chat"]
    assert chat and chat[0]["confidence"] == "low" and chat[0]["source_evidence_id"]
    # 사람용 텍스트는 narrative로 격리
    assert a["narrative"]["summary"]
    assert a["narrative"]["disclaimer"]


def test_analyze_persists_and_report(client):
    cid = _seed(client)
    posted = client.post(f"/cases/{cid}/analyze", json={}).json()
    got = client.get(f"/cases/{cid}/analysis").json()
    # /analyze 와 /analysis 가 '완전히 동일한' 스키마를 반환
    assert got["comparisons"] == posted["comparisons"]
    assert got["narrative"]["summary"] == posted["narrative"]["summary"]
    assert got["schema_version"] == posted["schema_version"]
    assert client.get(f"/cases/{cid}/report.html").status_code == 200
