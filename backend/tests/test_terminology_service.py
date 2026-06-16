from app.services.terminology_service import annotate_terms_for_language


def test_vietnamese_annotation_adds_parentheses_to_korean_terms():
    text = "급여명세서와 입금내역, 근로계약서를 준비하고 고용노동부에 문의하세요."

    result = annotate_terms_for_language(text, "vi")

    assert "급여명세서(bảng lương)" in result
    assert "입금내역(lịch sử chuyển khoản)" in result
    assert "근로계약서(hợp đồng lao động)" in result
    assert "고용노동부(Bộ Việc làm và Lao động)" in result


def test_vietnamese_annotation_does_not_duplicate_existing_annotation():
    text = "급여명세서(bảng lương)를 준비하세요."

    result = annotate_terms_for_language(text, "vi")

    assert result.count("급여명세서(bảng lương)") == 1
