"""확장 엔티티 필드 coercion 테스트."""
from providers.schema import ExtractedEntities


def test_확장필드_coercion():
    e = ExtractedEntities.model_validate({
        "work_days": "22일",
        "overtime_hours": "12.5",
        "night_hours": None,
        "holiday_hours": 8,
        "contract_start": "2026-01-01",
        "signed": "예",
    })
    assert e.work_days == 22
    assert e.overtime_hours == 12.5
    assert e.night_hours is None
    assert e.holiday_hours == 8.0
    assert e.signed is True


def test_서명_아니오_false():
    e = ExtractedEntities.model_validate({"signed": "없음"})
    assert e.signed is False


def test_확장필드_기본값_None():
    e = ExtractedEntities()
    assert e.work_days is None and e.overtime_hours is None and e.signed is None
