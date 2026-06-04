"""LLM provider — 문장화·요약만(생성). 계산 금지.

담당: 타임라인/요약 기능. `BedrockLlm`의 메서드를 채우면 끝.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from config import BEDROCK_MODEL_ID, PROVIDER_MODE


class LlmProvider(ABC):
    @abstractmethod
    def summarize_event(self, fact: str) -> str:
        """사건 사실 한 줄을 자연스러운 한국어 문장으로. 사실 추가/판단 금지."""

    @abstractmethod
    def summarize_case(self, facts: list[str]) -> str:
        """사실 목록 → 5~8문장 사건 요약. 수치 변경 금지, 끝에 면책."""


class MockLlm(LlmProvider):
    """로컬 기본값. 결정적 — 입력 사실을 그대로 사용(문장 다듬기 없음)."""

    def summarize_event(self, fact: str) -> str:
        return fact

    def summarize_case(self, facts: list[str]) -> str:
        body = " ".join(facts)
        return body + " 본 자료는 법률자문이 아닌 상담 준비용 정리입니다. 최종 판단은 전문기관에서 확인하세요."


class BedrockLlm(LlmProvider):
    """담당자 구현 지점. prompts/timeline.md, prompts/summary.md 사용."""

    def __init__(self):
        import boto3  # 지연 임포트
        self.client = boto3.client("bedrock-runtime")
        self.model = BEDROCK_MODEL_ID

    def summarize_event(self, fact: str) -> str:  # pragma: no cover
        raise NotImplementedError("Bedrock Text 호출 구현 (prompts/timeline.md)")

    def summarize_case(self, facts: list[str]) -> str:  # pragma: no cover
        raise NotImplementedError("Bedrock Text 호출 구현 (prompts/summary.md)")


def get_llm() -> LlmProvider:
    return BedrockLlm() if PROVIDER_MODE == "aws" else MockLlm()
