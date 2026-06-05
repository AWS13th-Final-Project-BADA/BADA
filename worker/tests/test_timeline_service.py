"""Unit tests for TimelineService (worker/services/timeline.py).

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 8.2, 8.4
- 6.1: description_translated is populated for non-ko languages
- 6.2: description_translated == description when target_lang is "ko"
- 6.3: original Korean description is preserved unchanged
- 6.4: graceful degradation — if translation fails, description_translated = description
- 8.2: both description and description_translated are present
- 8.4: source text never discarded or overwritten
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.timeline import build_timeline


# ── Fixtures ──


class MockLLM:
    """Mock LLM that returns input unchanged (identity function)."""

    def summarize_event(self, fact: str) -> str:
        return fact


class MockTranslatorIdentity:
    """Mock translator that returns input unchanged (simulates target_lang="ko")."""

    def translate(self, text: str, target_lang: str) -> str:
        return text

    def translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        return list(texts)


class MockTranslatorPrefix:
    """Mock translator that prepends '[vi]' to simulate non-ko translation."""

    def translate(self, text: str, target_lang: str) -> str:
        if target_lang == "ko" or not text:
            return text
        return f"[{target_lang}]{text}"

    def translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        if target_lang == "ko":
            return list(texts)
        return [self.translate(t, target_lang) for t in texts]


class MockTranslatorFailing:
    """Mock translator that simulates graceful degradation (returns source on failure)."""

    def translate(self, text: str, target_lang: str) -> str:
        # Simulates graceful degradation: returns source text
        return text

    def translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        # Simulates graceful degradation: returns source texts
        return list(texts)


@pytest.fixture
def llm():
    return MockLLM()


@pytest.fixture
def basic_ctx():
    return {
        "workplace_name": "○○제조",
        "work_start_date": "2024-01-15",
        "deposit_events": [
            {"date": "2024-02-28", "amount": 2300000},
        ],
    }


@pytest.fixture
def basic_result():
    return {
        "suspected_unpaid": 400000,
    }


# ── Test: description_translated is populated for non-ko ──


class TestTimelineTranslationNonKo:
    """Requirement 6.1: description_translated is populated for non-ko languages."""

    def test_description_translated_populated_for_vi(self, llm, basic_ctx, basic_result):
        translator = MockTranslatorPrefix()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="vi")

        assert len(timeline) > 0
        for event in timeline:
            assert "description_translated" in event
            assert event["description_translated"] != ""
            # MockTranslatorPrefix adds [vi] prefix
            assert event["description_translated"].startswith("[vi]")

    def test_description_translated_populated_for_en(self, llm, basic_ctx, basic_result):
        translator = MockTranslatorPrefix()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="en")

        for event in timeline:
            assert event["description_translated"].startswith("[en]")

    def test_both_description_and_translated_present(self, llm, basic_ctx, basic_result):
        """Requirement 8.2: both fields are always present."""
        translator = MockTranslatorPrefix()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="vi")

        for event in timeline:
            assert "description" in event
            assert "description_translated" in event
            assert event["description"] != ""
            assert event["description_translated"] != ""


# ── Test: description_translated == description when target_lang is "ko" ──


class TestTimelineKoreanTarget:
    """Requirement 6.2: description_translated == description when target is "ko"."""

    def test_ko_target_identity(self, llm, basic_ctx, basic_result):
        translator = MockTranslatorIdentity()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="ko")

        assert len(timeline) > 0
        for event in timeline:
            assert event["description_translated"] == event["description"]

    def test_ko_target_with_prefix_translator(self, llm, basic_ctx, basic_result):
        """Even a translator that normally prefixes should not modify for 'ko'."""
        translator = MockTranslatorPrefix()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="ko")

        for event in timeline:
            assert event["description_translated"] == event["description"]
            # No prefix should be added for ko
            assert not event["description_translated"].startswith("[ko]")

    def test_ko_target_empty_events(self, llm):
        """Edge case: no events produced, still returns empty list gracefully."""
        translator = MockTranslatorIdentity()
        timeline = build_timeline({}, {}, llm, translator, target_lang="ko")
        assert timeline == []


# ── Test: original description is never modified ──


class TestTimelineSourcePreservation:
    """Requirements 6.3, 8.4: original Korean description is preserved unchanged."""

    def test_description_unchanged_after_translation(self, llm, basic_ctx, basic_result):
        translator = MockTranslatorPrefix()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="vi")

        for event in timeline:
            # description should be plain Korean, not prefixed
            assert not event["description"].startswith("[vi]")
            # description should still contain Korean content
            assert any(c >= '\uac00' for c in event["description"])  # has Korean chars

    def test_description_not_overwritten_by_translation(self, llm, basic_ctx, basic_result):
        """Requirement 8.4: source text never discarded or overwritten."""
        translator = MockTranslatorPrefix()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="vi")

        # Verify description differs from description_translated when target != ko
        for event in timeline:
            assert event["description"] != event["description_translated"]
            # Original description is preserved as-is
            assert event["description"] in event["description_translated"].replace("[vi]", "")

    def test_ctx_not_modified_by_build_timeline(self, llm, basic_result):
        """The input ctx dict should not be modified by build_timeline."""
        ctx = {
            "workplace_name": "테스트사업장",
            "work_start_date": "2024-03-01",
            "deposit_events": [{"date": "2024-04-01", "amount": 1000000}],
        }
        ctx_copy = {
            "workplace_name": "테스트사업장",
            "work_start_date": "2024-03-01",
            "deposit_events": [{"date": "2024-04-01", "amount": 1000000}],
        }
        translator = MockTranslatorPrefix()
        build_timeline(ctx, basic_result, llm, translator, target_lang="vi")

        assert ctx == ctx_copy


# ── Test: graceful degradation ──


class TestTimelineGracefulDegradation:
    """Requirement 6.4: if translation fails, description_translated = description."""

    def test_failing_translator_returns_source_as_translated(self, llm, basic_ctx, basic_result):
        """When translator returns source (graceful degradation), description_translated = description."""
        translator = MockTranslatorFailing()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="vi")

        assert len(timeline) > 0
        for event in timeline:
            # Failing translator returns source text → description_translated == description
            assert event["description_translated"] == event["description"]

    def test_graceful_degradation_still_produces_valid_timeline(self, llm, basic_ctx, basic_result):
        """Timeline is still structurally valid even when translation fails."""
        translator = MockTranslatorFailing()
        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="vi")

        for event in timeline:
            assert "date" in event
            assert "type" in event
            assert "description" in event
            assert "description_translated" in event
            assert event["description"] != ""


# ── Test: translate_batch is used (efficiency) ──


class TestTimelineBatchTranslation:
    """Verify translate_batch is called instead of individual translate calls."""

    def test_translate_batch_called_once(self, llm, basic_ctx, basic_result):
        """translate_batch should be called exactly once for all descriptions."""
        translator = MagicMock()
        translator.translate_batch.return_value = [
            "[vi]2024-01-15, ○○제조에서 근무를 시작했습니다.",
            "[vi]2024-02-28, 2,300,000원이 입금되었습니다.",
            "[vi]미지급 의심 금액 약 400,000원이 확인됩니다. (확정 아님, 확인 필요)",
        ]

        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="vi")

        # translate_batch should be called exactly once
        translator.translate_batch.assert_called_once()
        # translate (individual) should NOT be called
        translator.translate.assert_not_called()

    def test_translate_batch_receives_all_descriptions(self, llm, basic_ctx, basic_result):
        """translate_batch receives the full list of descriptions."""
        translator = MagicMock()
        translator.translate_batch.return_value = ["a", "b", "c"]

        build_timeline(basic_ctx, basic_result, llm, translator, target_lang="vi")

        call_args = translator.translate_batch.call_args
        descriptions_arg = call_args[0][0]  # first positional arg
        target_lang_arg = call_args[0][1]   # second positional arg

        assert len(descriptions_arg) == 3
        assert target_lang_arg == "vi"

    def test_translate_batch_called_with_ko_target(self, llm, basic_ctx, basic_result):
        """Even for ko target, translate_batch is still called (it handles the no-op internally)."""
        translator = MagicMock()
        # translate_batch for "ko" returns input unchanged
        translator.translate_batch.side_effect = lambda texts, lang: list(texts)

        timeline = build_timeline(basic_ctx, basic_result, llm, translator, target_lang="ko")

        translator.translate_batch.assert_called_once()
        for event in timeline:
            assert event["description_translated"] == event["description"]
