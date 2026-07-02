"""LLM provider — 문장화·요약만(생성). 계산 금지.

local=Mock(항등), aws=Bedrock Claude(실제 호출). 전환은 PROVIDER_MODE.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from config import PROVIDER_MODE

_FORBID = "금지 표현(불법/확정/무조건/바로 신고)을 쓰지 말고, 미지급 '의심'·'확인 필요' 톤만 사용하세요."


class LlmProvider(ABC):
    @abstractmethod
    def summarize_event(self, fact: str) -> str: ...

    @abstractmethod
    def summarize_case(self, facts: list[str], lang: str = "ko") -> str: ...


class MockLlm(LlmProvider):
    """로컬 기본값. 결정적 — 입력 사실을 그대로 사용."""

    def summarize_event(self, fact: str) -> str:
        return fact

    def summarize_case(self, facts: list[str], lang: str = "ko") -> str:
        return " ".join(facts) + " 본 자료는 법률자문이 아닌 상담 준비용 정리입니다. 최종 판단은 전문기관에서 확인하세요."


class BedrockLlm(LlmProvider):
    """Bedrock Claude Text 실제 호출. 사실 추가/판단 금지, 문장만 다듬음."""

    def summarize_event(self, fact: str) -> str:
        from providers import _bedrock
        system = f"주어진 사실을 자연스러운 한국어 한 문장으로 정리하세요. 사실을 추가하거나 판단하지 마세요. {_FORBID}"
        return _bedrock.invoke(system, [_bedrock.text_block(f"사실: {fact}\n한 문장:")], max_tokens=300).strip()

    def summarize_case(self, facts: list[str], lang: str = "ko") -> str:
        from providers import _bedrock
        lang_instruction = "" if lang == "ko" else f" 반드시 {lang} 언어로 작성하세요."
        system = (f"상담 준비용 사건 요약을 5~8문장으로 쓰세요. 주어진 수치를 바꾸지 말고 새 수치를 만들지 마세요. "
                  f"{_FORBID} 마지막 문장에 '본 자료는 법률자문이 아닌 상담 준비용 정리이며 최종 판단은 전문기관에서 확인해야 합니다'를 넣으세요.{lang_instruction}")
        body = "\n".join(f"- {f}" for f in facts)
        return _bedrock.invoke(system, [_bedrock.text_block(f"사실 목록:\n{body}\n\n요약:")], max_tokens=800).strip()


def get_llm() -> LlmProvider:
    return BedrockLlm() if PROVIDER_MODE == "aws" else MockLlm()
