from app.db import SessionLocal
from app.models import User
from app.services import auth_service


def _auth_headers() -> dict[str, str]:
    db = SessionLocal()
    try:
        user = User(email="mobile-e2e@example.com", name="Mobile E2E", preferred_lang="ko")
        db.add(user)
        db.commit()
        db.refresh(user)
        token = auth_service.create_access_token(sub=user.id, email=user.email, name=user.name)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


def test_mobile_login_case_upload_chat_flow(client, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "storage_mode", "local")
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    headers = _auth_headers()

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "mobile-e2e@example.com"

    case_res = client.post(
        "/cases",
        headers=headers,
        json={
            "workplace_name": "바다식품",
            "employer_name": "김대표",
            "work_start_date": "2026-06-01",
            "agreed_hourly_wage": 10030,
            "issue_types": ["wage_unpaid", "deduction"],
        },
    )
    assert case_res.status_code == 200
    case_id = case_res.json()["id"]

    upload_res = client.post(
        f"/cases/{case_id}/evidences/upload",
        headers=headers,
        data={"category": "statement"},
        files={"file": ("payslip.pdf", b"%PDF-1.4\nfake-pdf", "application/pdf")},
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["file_name"] == "payslip.pdf"

    listed = client.get(f"/cases/{case_id}/evidences", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    chat = client.post(
        "/chat/messages",
        headers=headers,
        json={
            "case_id": case_id,
            "message": "상담하러 가면 뭐부터 말하면 좋을까요?",
            "language": "ko",
        },
    )
    assert chat.status_code == 200
    assert chat.json()["answer"]
