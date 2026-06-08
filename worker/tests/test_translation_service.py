"""Unit tests for TranslationService (build_translation_pairs).

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 8.1
"""
from __future__ import annotations

import pytest

from services.translation import DISCLAIMER_TEXT, build_translation_pairs


# ── Test helpers ──


class IdentityTranslator:
    """Mock translator that returns source text unchanged (identity)."""

    def translate(self, text: str, target_lang: str) -> str:
        return text


class PrefixTranslator:
    """Mock translator that prefixes text with [vi] to verify translation was called."""

    def translate(self, text: str, target_lang: str) -> str:
        if target_lang == "ko":
            return text
        return f"[{target_lang}]{text}"


class FailingTranslator:
    """Mock translator that always raises an exception."""

    def translate(self, text: str, target_lang: str) -> str:
        raise RuntimeError("API unavailable")


class EmptyTranslator:
    """Mock translator that returns empty string (simulates edge case)."""

    def translate(self, text: str, target_lang: str) -> str:
        return ""


# ── Disclaimer tests (Requirement 5.3) ──


class TestDisclaimerPair:
    """면책 고지 TranslationPair is always included."""

    def test_disclaimer_present_with_empty_result(self):
        """Disclaimer is included even when result has no deductions or unpaid."""
        pairs = build_translation_pairs({}, {}, IdentityTranslator(), "vi")
        assert len(pairs) >= 1
        disclaimer_pairs = [p for p in pairs if p["related_issue"] == "disclaimer"]
        assert len(disclaimer_pairs) == 1

    def test_disclaimer_present_with_deductions(self):
        """Disclaimer is included alongside deduction pairs."""
        result = {
            "deduction_items": [
                {"name": "기숙사비", "amount": 250000, "check": "계약서 명시 확인 필요"}
            ]
        }
        pairs = build_translation_pairs({}, result, IdentityTranslator(), "vi")
        disclaimer_pairs = [p for p in pairs if p["related_issue"] == "disclaimer"]
        assert len(disclaimer_pairs) == 1

    def test_disclaimer_has_correct_evidence_type(self):
        """Disclaimer pair has evidence_type = '면책 고지'."""
        pairs = build_translation_pairs({}, {}, IdentityTranslator(), "vi")
        disclaimer = next(p for p in pairs if p["related_issue"] == "disclaimer")
        assert disclaimer["evidence_type"] == "면책 고지"

    def test_disclaimer_source_text_is_known_content(self):
        """Disclaimer source_text matches the defined DISCLAIMER_TEXT constant."""
        pairs = build_translation_pairs({}, {}, IdentityTranslator(), "vi")
        disclaimer = next(p for p in pairs if p["related_issue"] == "disclaimer")
        assert disclaimer["source_text"] == DISCLAIMER_TEXT

    def test_disclaimer_translated_with_prefix_translator(self):
        """Disclaimer is translated using the provided translator."""
        pairs = build_translation_pairs({}, {}, PrefixTranslator(), "vi")
        disclaimer = next(p for p in pairs if p["related_issue"] == "disclaimer")
        assert disclaimer["translated_text"].startswith("[vi]")


# ── Deduction pair tests (Requirement 5.1) ──


class TestDeductionPairs:
    """Deduction items produce correct TranslationPairs."""

    def test_single_deduction(self):
        result = {
            "deduction_items": [
                {"name": "기숙사비", "amount": 250000, "check": "계약서 명시 확인 필요"}
            ]
        }
        pairs = build_translation_pairs({}, result, PrefixTranslator(), "vi")
        deduction_pairs = [p for p in pairs if p["related_issue"] == "deduction"]
        assert len(deduction_pairs) == 1
        assert "기숙사비" in deduction_pairs[0]["source_text"]
        assert "250,000원" in deduction_pairs[0]["source_text"]
        assert deduction_pairs[0]["evidence_type"] == "급여명세서/공제"

    def test_multiple_deductions(self):
        result = {
            "deduction_items": [
                {"name": "기숙사비", "amount": 250000, "check": "확인 필요"},
                {"name": "식비", "amount": 100000, "check": "확인 필요"},
            ]
        }
        pairs = build_translation_pairs({}, result, IdentityTranslator(), "vi")
        deduction_pairs = [p for p in pairs if p["related_issue"] == "deduction"]
        assert len(deduction_pairs) == 2

    def test_no_deductions_no_deduction_pairs(self):
        result = {"deduction_items": []}
        pairs = build_translation_pairs({}, result, IdentityTranslator(), "vi")
        deduction_pairs = [p for p in pairs if p["related_issue"] == "deduction"]
        assert len(deduction_pairs) == 0


# ── Suspected unpaid tests (Requirement 5.2) ──


class TestSuspectedUnpaidPair:
    """suspected_unpaid pair only when amount > 0."""

    def test_unpaid_pair_when_positive(self):
        result = {"suspected_unpaid": 400000}
        pairs = build_translation_pairs({}, result, PrefixTranslator(), "vi")
        unpaid_pairs = [p for p in pairs if p["related_issue"] == "wage_unpaid"]
        assert len(unpaid_pairs) == 1
        assert "400,000원" in unpaid_pairs[0]["source_text"]
        assert unpaid_pairs[0]["evidence_type"] == "사용자 진술"

    def test_no_unpaid_pair_when_zero(self):
        result = {"suspected_unpaid": 0}
        pairs = build_translation_pairs({}, result, IdentityTranslator(), "vi")
        unpaid_pairs = [p for p in pairs if p["related_issue"] == "wage_unpaid"]
        assert len(unpaid_pairs) == 0

    def test_no_unpaid_pair_when_missing(self):
        result = {}
        pairs = build_translation_pairs({}, result, IdentityTranslator(), "vi")
        unpaid_pairs = [p for p in pairs if p["related_issue"] == "wage_unpaid"]
        assert len(unpaid_pairs) == 0


# ── Missing evidence tests ──


class TestMissingEvidencePairs:
    """missing_evidences list produces TranslationPairs."""

    def test_missing_evidences_generates_pairs(self):
        result = {
            "missing_evidences": [
                {"item": "통장 입금내역", "reason": "급여 수령 확인을 위해 필요합니다"},
                {"item": "근무표", "reason": "근무시간 확인을 위해 필요합니다"},
            ]
        }
        pairs = build_translation_pairs({}, result, PrefixTranslator(), "vi")
        missing_pairs = [p for p in pairs if p["related_issue"] == "missing_evidence"]
        assert len(missing_pairs) == 2
        assert "통장 입금내역" in missing_pairs[0]["source_text"]
        assert missing_pairs[0]["evidence_type"] == "누락 자료 안내"

    def test_no_missing_evidences_no_pairs(self):
        result = {"missing_evidences": []}
        pairs = build_translation_pairs({}, result, IdentityTranslator(), "vi")
        missing_pairs = [p for p in pairs if p["related_issue"] == "missing_evidence"]
        assert len(missing_pairs) == 0

    def test_missing_evidences_key_absent(self):
        result = {}
        pairs = build_translation_pairs({}, result, IdentityTranslator(), "vi")
        missing_pairs = [p for p in pairs if p["related_issue"] == "missing_evidence"]
        assert len(missing_pairs) == 0

    def test_missing_evidence_source_contains_item_and_reason(self):
        result = {
            "missing_evidences": [
                {"item": "계약서", "reason": "사업장 정보 확인 필요"}
            ]
        }
        pairs = build_translation_pairs({}, result, IdentityTranslator(), "vi")
        missing_pairs = [p for p in pairs if p["related_issue"] == "missing_evidence"]
        assert "계약서" in missing_pairs[0]["source_text"]
        assert "사업장 정보 확인 필요" in missing_pairs[0]["source_text"]


# ── Graceful degradation tests (Requirements 5.4, 5.5) ──


class TestGracefulDegradation:
    """Translator failure still produces valid pairs with source_text as fallback."""

    def test_failing_translator_produces_valid_pairs(self):
        """When translator raises, pairs still have non-empty source_text and translated_text."""
        result = {
            "deduction_items": [
                {"name": "기숙사비", "amount": 250000, "check": "확인 필요"}
            ],
            "suspected_unpaid": 400000,
            "missing_evidences": [
                {"item": "통장", "reason": "필요"}
            ],
        }
        pairs = build_translation_pairs({}, result, FailingTranslator(), "vi")

        # All pairs should still be valid
        assert len(pairs) >= 4  # disclaimer + 1 deduction + unpaid + 1 missing
        for pair in pairs:
            assert pair["source_text"]  # non-empty
            assert pair["translated_text"]  # non-empty
            assert pair["evidence_type"]  # present
            assert pair["related_issue"]  # present
            # On failure, translated_text falls back to source_text
            assert pair["translated_text"] == pair["source_text"]

    def test_empty_translator_falls_back_to_source(self):
        """When translator returns empty string, pair uses source_text as fallback."""
        result = {}
        pairs = build_translation_pairs({}, result, EmptyTranslator(), "vi")
        disclaimer = next(p for p in pairs if p["related_issue"] == "disclaimer")
        # Fallback: translated_text == source_text (never empty)
        assert disclaimer["translated_text"] == disclaimer["source_text"]
        assert disclaimer["translated_text"] != ""


# ── Pair completeness tests (Requirements 5.4, 5.5, 5.6, 8.1) ──


class TestPairCompleteness:
    """Every pair has non-empty source_text, translated_text, evidence_type, related_issue."""

    def test_all_pairs_have_required_fields(self):
        """Full result produces pairs where every field is present and non-empty."""
        result = {
            "deduction_items": [
                {"name": "기숙사비", "amount": 250000, "check": "확인 필요"},
                {"name": "식비", "amount": 100000, "check": "확인 필요"},
            ],
            "suspected_unpaid": 400000,
            "missing_evidences": [
                {"item": "통장 입금내역", "reason": "급여 확인"},
                {"item": "근무표", "reason": "시간 확인"},
            ],
        }
        pairs = build_translation_pairs({}, result, PrefixTranslator(), "vi")

        # Expected: 1 disclaimer + 2 deductions + 1 unpaid + 2 missing = 6
        assert len(pairs) == 6

        for pair in pairs:
            assert "source_text" in pair and pair["source_text"]
            assert "translated_text" in pair and pair["translated_text"]
            assert "evidence_type" in pair and pair["evidence_type"]
            assert "related_issue" in pair and pair["related_issue"]
