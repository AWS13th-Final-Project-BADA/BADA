"""음성 전사 provider 모드가 전체 provider 모드와 독립적으로 동작하는지 검증."""

from providers import transcribe


def test_transcribe_mode_local_uses_mock(monkeypatch):
    monkeypatch.setattr(transcribe, "TRANSCRIBE_MODE", "local")

    provider = transcribe.get_transcriber()

    assert isinstance(provider, transcribe.MockTranscriber)


def test_transcribe_mode_aws_uses_amazon(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(transcribe, "TRANSCRIBE_MODE", "aws")
    monkeypatch.setattr(transcribe, "AmazonTranscriber", lambda region: sentinel)

    provider = transcribe.get_transcriber()

    assert provider is sentinel
