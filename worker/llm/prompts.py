"""prompts/ 디렉토리의 마크다운 프롬프트를 로드."""
from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load(name: str) -> str:
    """name 예: 'extraction' → prompts/extraction.md"""
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")
