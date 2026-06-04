from security.pii import mask_pii


def test_masks_account_rrn_phone():
    text = "계좌 110-234-567890 으로 입금. 주민 900101-1234567, 연락처 010-1234-5678"
    out = mask_pii(text)
    assert "[ACCOUNT]" in out
    assert "[RRN]" in out
    assert "[PHONE]" in out
    assert "110-234-567890" not in out
    assert "900101-1234567" not in out


def test_plain_text_unchanged():
    assert mask_pii("기숙사비 25만원 공제") == "기숙사비 25만원 공제"
