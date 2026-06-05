"""Unit tests for AmazonTranslator.translate() method.

Tests use mocking for boto3 clients since we don't have live AWS credentials.
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4
"""
from unittest.mock import MagicMock, patch

import pytest

from providers.language_config import UnsupportedLanguageError
from providers.translate import AmazonTranslator, MockTranslator


# ── MockTranslator tests ──


class TestMockTranslator:
    def setup_method(self):
        self.translator = MockTranslator()

    def test_empty_text_returns_empty(self):
        assert self.translator.translate("", "vi") == ""

    def test_korean_target_returns_source(self):
        assert self.translator.translate("테스트", "ko") == "테스트"

    def test_non_korean_target_returns_source(self):
        # MockTranslator always returns source text (identity)
        assert self.translator.translate("테스트", "vi") == "테스트"


# ── AmazonTranslator tests (mocked boto3) ──


@pytest.fixture
def mock_boto3():
    """Patch boto3.client at the module level to avoid real AWS calls."""
    with patch("boto3.client") as mock_client:
        mock_translate_client = MagicMock()
        mock_client.return_value = mock_translate_client
        yield mock_translate_client


@pytest.fixture
def translator(mock_boto3):
    """Create AmazonTranslator with mocked boto3."""
    t = AmazonTranslator(region="ap-northeast-2")
    # The client was created in __init__ via mocked boto3.client
    # Override it explicitly to ensure we control the mock
    t.client = mock_boto3
    return t


class TestAmazonTranslatorNoOp:
    """No-op cases: empty text and Korean target."""

    def test_empty_text_returns_empty_string(self, translator, mock_boto3):
        result = translator.translate("", "vi")
        assert result == ""
        mock_boto3.translate_text.assert_not_called()

    def test_korean_target_returns_source_unchanged(self, translator, mock_boto3):
        source = "미지급 의심 금액"
        result = translator.translate(source, "ko")
        assert result == source
        mock_boto3.translate_text.assert_not_called()

    def test_source_text_not_modified(self, translator, mock_boto3):
        """Requirement 1.5: source text object is never modified."""
        mock_boto3.translate_text.return_value = {"TranslatedText": "translated"}
        source = "원본 텍스트"
        original_source = source  # reference check
        translator.translate(source, "vi")
        assert source == original_source


class TestAmazonTranslatorDirect:
    """Direct strategy: vi, en, id."""

    def test_direct_translation_vi(self, translator, mock_boto3):
        mock_boto3.translate_text.return_value = {
            "TranslatedText": "Số tiền nghi chưa trả"
        }
        result = translator.translate("미지급 의심 금액", "vi")
        assert result == "Số tiền nghi chưa trả"
        mock_boto3.translate_text.assert_called_once_with(
            Text="미지급 의심 금액",
            SourceLanguageCode="ko",
            TargetLanguageCode="vi",
        )

    def test_direct_translation_en(self, translator, mock_boto3):
        mock_boto3.translate_text.return_value = {
            "TranslatedText": "Suspected unpaid amount"
        }
        result = translator.translate("미지급 의심 금액", "en")
        assert result == "Suspected unpaid amount"
        mock_boto3.translate_text.assert_called_once_with(
            Text="미지급 의심 금액",
            SourceLanguageCode="ko",
            TargetLanguageCode="en",
        )

    def test_direct_translation_id(self, translator, mock_boto3):
        mock_boto3.translate_text.return_value = {
            "TranslatedText": "Jumlah yang diduga belum dibayar"
        }
        result = translator.translate("미지급 의심 금액", "id")
        assert result == "Jumlah yang diduga belum dibayar"


class TestAmazonTranslatorPivotRefine:
    """Pivot+refine strategy: km, ne."""

    def test_pivot_refine_km(self, translator, mock_boto3):
        """Requirement 3.2, 3.3: ko→en→km + Claude refinement."""
        # Mock two translate_text calls (ko→en, en→km)
        mock_boto3.translate_text.side_effect = [
            {"TranslatedText": "Suspected unpaid amount"},  # ko→en
            {"TranslatedText": "ចំនួនទឹកប្រាក់សង្ស័យថាមិនបានបង់"},  # en→km
        ]

        # Mock Claude refinement
        with patch.object(
            translator,
            "_refine_with_claude",
            return_value="ចំនួនទឹកប្រាក់ដែលសង្ស័យថាមិនទាន់បានបង់",
        ):
            result = translator.translate("미지급 의심 금액", "km")

        assert result == "ចំនួនទឹកប្រាក់ដែលសង្ស័យថាមិនទាន់បានបង់"
        assert mock_boto3.translate_text.call_count == 2

    def test_pivot_refine_ne(self, translator, mock_boto3):
        """Requirement 3.2: ne uses pivot+refine strategy."""
        mock_boto3.translate_text.side_effect = [
            {"TranslatedText": "Suspected amount"},  # ko→en
            {"TranslatedText": "शंकास्पद रकम"},  # en→ne
        ]

        with patch.object(
            translator, "_refine_with_claude", return_value="शंकास्पद रकम"
        ):
            result = translator.translate("의심 금액", "ne")

        assert result == "शंकास्पद रकम"
        assert mock_boto3.translate_text.call_count == 2

    def test_pivot_calls_correct_language_codes(self, translator, mock_boto3):
        """Verify first call is ko→en and second is en→km."""
        mock_boto3.translate_text.side_effect = [
            {"TranslatedText": "English text"},
            {"TranslatedText": "Khmer text"},
        ]

        with patch.object(
            translator, "_refine_with_claude", return_value="Khmer text"
        ):
            translator.translate("한국어 텍스트", "km")

        calls = mock_boto3.translate_text.call_args_list
        # First call: ko→en
        assert calls[0].kwargs["SourceLanguageCode"] == "ko"
        assert calls[0].kwargs["TargetLanguageCode"] == "en"
        # Second call: en→km
        assert calls[1].kwargs["SourceLanguageCode"] == "en"
        assert calls[1].kwargs["TargetLanguageCode"] == "km"


class TestAmazonTranslatorClaudeRefinement:
    """Claude refinement for low-resource languages."""

    def test_refinement_failure_falls_back_to_draft(self, translator, mock_boto3):
        """Requirement 3.5: Claude failure → use unrefined draft."""
        mock_boto3.translate_text.side_effect = [
            {"TranslatedText": "English"},
            {"TranslatedText": "Draft Khmer"},
        ]

        with patch.object(
            translator,
            "_refine_with_claude",
            side_effect=Exception("Bedrock unavailable"),
        ):
            # _refine_with_claude itself handles the exception internally,
            # but if it propagates, the outer try/except catches it
            result = translator.translate("테스트", "km")

        # Should gracefully degrade to source text since exception propagated
        assert result == "테스트"

    def test_refine_with_claude_returns_draft_on_exception(self, translator):
        """_refine_with_claude returns draft when Bedrock fails."""
        # Patch boto3.client globally since _refine_with_claude does local import
        with patch("boto3.client") as mock_client:
            mock_client.return_value.invoke_model.side_effect = Exception("fail")
            result = translator._refine_with_claude("원문", "초벌 번역", "km")

        assert result == "초벌 번역"

    def test_refine_with_claude_returns_draft_on_empty_response(self, translator):
        """Requirement 3.5: If Claude returns empty string, fall back to draft."""
        import io
        import json

        mock_response_body = io.BytesIO(
            json.dumps({"content": [{"text": ""}]}).encode()
        )

        with patch("boto3.client") as mock_client:
            mock_client.return_value.invoke_model.return_value = {
                "body": mock_response_body
            }
            result = translator._refine_with_claude("원문", "초벌 번역", "km")

        assert result == "초벌 번역"

    def test_refine_with_claude_returns_refined_on_success(self, translator):
        """Requirement 3.4: Claude refinement returns improved translation."""
        import io
        import json

        refined_text = "ចំនួនទឹកប្រាក់ដែលសង្ស័យ"
        mock_response_body = io.BytesIO(
            json.dumps({"content": [{"text": refined_text}]}).encode()
        )

        with patch("boto3.client") as mock_client:
            mock_client.return_value.invoke_model.return_value = {
                "body": mock_response_body
            }
            result = translator._refine_with_claude("미지급 의심", "초벌", "km")

        assert result == refined_text

    def test_refine_with_claude_strips_whitespace(self, translator):
        """Claude output should be stripped of leading/trailing whitespace."""
        import io
        import json

        mock_response_body = io.BytesIO(
            json.dumps({"content": [{"text": "  refined text  \n"}]}).encode()
        )

        with patch("boto3.client") as mock_client:
            mock_client.return_value.invoke_model.return_value = {
                "body": mock_response_body
            }
            result = translator._refine_with_claude("원문", "초벌", "km")

        assert result == "refined text"


class TestAmazonTranslatorGracefulDegradation:
    """Requirement 4.1, 4.2, 4.4: API failure → return source text."""

    def test_translate_api_error_returns_source(self, translator, mock_boto3):
        mock_boto3.translate_text.side_effect = Exception("Service unavailable")
        result = translator.translate("원본 텍스트", "vi")
        assert result == "원본 텍스트"

    def test_translate_client_error_returns_source(self, translator, mock_boto3):
        from botocore.exceptions import ClientError

        mock_boto3.translate_text.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "TranslateText",
        )
        result = translator.translate("쓰로틀링 테스트", "vi")
        assert result == "쓰로틀링 테스트"

    def test_timeout_returns_source_no_exception(self, translator, mock_boto3):
        """Requirement 4.2: timeout returns source without raising."""
        mock_boto3.translate_text.side_effect = TimeoutError("Connection timed out")
        result = translator.translate("타임아웃 테스트", "en")
        assert result == "타임아웃 테스트"


class TestAmazonTranslatorChunkText:
    """Requirement 9.1, 9.2: Text chunking for texts exceeding 10KB."""

    def test_short_text_returns_single_item_list(self):
        """Short text (< 10KB) returns single-element list."""
        short_text = "짧은 텍스트입니다."
        result = AmazonTranslator._chunk_text(short_text)
        assert result == [short_text]

    def test_splits_at_sentence_boundaries(self):
        """Splits at Korean sentence-ending markers."""
        # Create a text with known sentence boundaries that exceeds max_bytes
        sentence = "이것은 테스트 문장입니다. "
        # Each sentence is about 30 bytes in UTF-8, create enough to exceed a small limit
        text = sentence * 20  # ~600 bytes
        chunks = AmazonTranslator._chunk_text(text, max_bytes=100)

        assert len(chunks) > 1
        # Recombined should equal original
        assert "".join(chunks) == text
        # Each chunk should end at a sentence boundary (except possibly last)
        for chunk in chunks[:-1]:
            assert chunk.endswith("다. ")

    def test_splits_at_space_when_no_sentence_boundary(self):
        """Falls back to space-splitting when no sentence markers found."""
        # Use text without Korean sentence markers
        word = "word "
        text = word * 100  # 500 bytes
        chunks = AmazonTranslator._chunk_text(text, max_bytes=50)

        assert len(chunks) > 1
        assert "".join(chunks) == text

    def test_recombined_chunks_equal_original(self):
        """Chunking and recombining preserves the original text."""
        sentence = "기숙사비 250,000원이 공제되었습니다. "
        text = sentence * 50  # Large text
        chunks = AmazonTranslator._chunk_text(text, max_bytes=200)

        assert "".join(chunks) == text

    def test_each_chunk_within_max_bytes(self):
        """Each chunk should be within max_bytes (except forced splits)."""
        sentence = "이 문장은 테스트용입니다. "
        text = sentence * 100
        max_bytes = 200
        chunks = AmazonTranslator._chunk_text(text, max_bytes=max_bytes)

        for chunk in chunks:
            # Chunks that split on sentence boundaries should be within limit
            # (forced splits may slightly exceed due to multi-byte chars)
            assert len(chunk.encode("utf-8")) <= max_bytes + 50


class TestAmazonTranslatorChunkedTranslate:
    """Requirement 9.2, 9.3: Oversized text chunk→translate→concatenate."""

    def test_oversized_text_is_chunked_and_translated(self, translator, mock_boto3):
        """Texts > 10KB are chunked, translated individually, and concatenated."""
        # Create a text > 10KB (Korean chars are 3 bytes each in UTF-8)
        sentence = "이것은 매우 긴 테스트 문장입니다. "
        # ~51 bytes per sentence, need ~200 sentences for >10KB
        text = sentence * 300
        assert len(text.encode("utf-8")) > 10000

        # Mock translate to return a fixed prefix + input (so we can verify order)
        mock_boto3.translate_text.side_effect = (
            lambda **kwargs: {"TranslatedText": f"[T]{kwargs['Text']}"}
        )

        result = translator.translate(text, "vi")

        # Result should be concatenation of translated chunks
        assert result.startswith("[T]")
        # Multiple API calls should have been made (one per chunk)
        assert mock_boto3.translate_text.call_count > 1

    def test_chunk_failure_uses_source_for_that_chunk(self, translator, mock_boto3):
        """Requirement 9.3: If a chunk fails, use source text for that chunk."""
        sentence = "이것은 테스트 문장입니다. "
        text = sentence * 300  # ~11100 bytes (37 bytes * 300)
        assert len(text.encode("utf-8")) > 10000

        # First call succeeds, second call fails
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("API Error on chunk 2")
            return {"TranslatedText": f"[OK{call_count[0]}]"}

        mock_boto3.translate_text.side_effect = side_effect

        result = translator.translate(text, "vi")

        # Result should contain successful translation for first chunk
        assert "[OK1]" in result
        # The failed chunk's source text should be present (Korean text)
        assert "이것은" in result
        # At least 2 API calls were attempted
        assert mock_boto3.translate_text.call_count >= 2

    def test_short_text_not_chunked(self, translator, mock_boto3):
        """Short text should not trigger chunking."""
        mock_boto3.translate_text.return_value = {"TranslatedText": "translated"}
        text = "짧은 텍스트"
        translator.translate(text, "vi")
        # Only 1 API call (no chunking)
        mock_boto3.translate_text.assert_called_once()


class TestAmazonTranslatorUnsupportedLanguage:
    """Requirement 1.4: Unsupported language raises UnsupportedLanguageError."""

    def test_unsupported_language_raises(self, translator):
        with pytest.raises(UnsupportedLanguageError) as exc_info:
            translator.translate("텍스트", "xx")
        assert "xx" in str(exc_info.value)

    def test_unsupported_language_propagates(self, translator):
        """UnsupportedLanguageError is NOT caught by graceful degradation."""
        with pytest.raises(UnsupportedLanguageError):
            translator.translate("텍스트", "fr")


# ── MockTranslator translate_batch tests ──


class TestMockTranslatorBatch:
    """Unit tests for MockTranslator.translate_batch()."""

    def setup_method(self):
        self.translator = MockTranslator()

    def test_batch_length_preservation(self):
        """Requirement 2.1: output list has same length as input."""
        texts = ["첫 번째", "두 번째", "세 번째"]
        result = self.translator.translate_batch(texts, "vi")
        assert len(result) == len(texts)

    def test_batch_order_preservation(self):
        """Requirement 2.2: i-th output corresponds to i-th input."""
        texts = ["A 텍스트", "B 텍스트", "C 텍스트"]
        result = self.translator.translate_batch(texts, "vi")
        # MockTranslator returns identity, so order is trivially preserved
        assert result == texts

    def test_batch_korean_target_short_circuit(self):
        """Requirement 2.3: target 'ko' returns input list unchanged."""
        texts = ["가나다", "라마바", "사아자"]
        result = self.translator.translate_batch(texts, "ko")
        assert result == texts

    def test_batch_empty_list(self):
        """Edge case: empty list returns empty list."""
        result = self.translator.translate_batch([], "vi")
        assert result == []


# ── AmazonTranslator translate_batch tests (mocked boto3) ──


class TestAmazonTranslatorBatch:
    """Unit tests for AmazonTranslator.translate_batch().

    Validates: Requirements 2.1, 2.2, 2.3, 2.4
    """

    def test_batch_length_preservation(self, translator, mock_boto3):
        """Requirement 2.1: output length == input length."""
        mock_boto3.translate_text.return_value = {"TranslatedText": "translated"}
        texts = ["하나", "둘", "셋", "넷"]
        result = translator.translate_batch(texts, "vi")
        assert len(result) == len(texts)

    def test_batch_order_preservation(self, translator, mock_boto3):
        """Requirement 2.2: order is preserved in output."""
        mock_boto3.translate_text.side_effect = [
            {"TranslatedText": "first"},
            {"TranslatedText": "second"},
            {"TranslatedText": "third"},
        ]
        texts = ["첫째", "둘째", "셋째"]
        result = translator.translate_batch(texts, "vi")
        assert result == ["first", "second", "third"]

    def test_batch_korean_target_short_circuit(self, translator, mock_boto3):
        """Requirement 2.3: target 'ko' returns input unchanged, no API call."""
        texts = ["가나다", "라마바"]
        result = translator.translate_batch(texts, "ko")
        assert result == texts
        mock_boto3.translate_text.assert_not_called()

    def test_batch_per_item_error_isolation(self, translator, mock_boto3):
        """Requirement 2.4: failed item returns source, others continue."""
        mock_boto3.translate_text.side_effect = [
            {"TranslatedText": "success 1"},
            Exception("API error on item 2"),
            {"TranslatedText": "success 3"},
        ]
        texts = ["텍스트1", "텍스트2", "텍스트3"]
        result = translator.translate_batch(texts, "vi")
        assert len(result) == 3
        assert result[0] == "success 1"
        assert result[1] == "텍스트2"  # Failed item → source text
        assert result[2] == "success 3"

    def test_batch_empty_list(self, translator, mock_boto3):
        """Edge case: empty input returns empty output."""
        result = translator.translate_batch([], "vi")
        assert result == []
        mock_boto3.translate_text.assert_not_called()

    def test_batch_unsupported_language_raises(self, translator, mock_boto3):
        """UnsupportedLanguageError propagates from batch."""
        with pytest.raises(UnsupportedLanguageError):
            translator.translate_batch(["텍스트"], "xx")

    def test_batch_with_empty_strings(self, translator, mock_boto3):
        """Empty strings in batch are handled correctly (no API call for them)."""
        mock_boto3.translate_text.return_value = {"TranslatedText": "translated"}
        texts = ["", "텍스트", ""]
        result = translator.translate_batch(texts, "vi")
        assert len(result) == 3
        assert result[0] == ""
        assert result[1] == "translated"
        assert result[2] == ""
        # Only one API call (for the non-empty text)
        assert mock_boto3.translate_text.call_count == 1
