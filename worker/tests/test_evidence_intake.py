"""증거 수집 에이전트 — 스캔/배치 단계 동작 테스트.

로컬(PROVIDER_MODE != aws)에서는 classify가 보류값(other/low/relevant=True)을 주므로
'무관 제외'와 '등급화' 흐름을 결정적으로 검증한다(실제 LLM 호출 없음).
"""
import config
from services.evidence_intake import (
    DECISION_REJECT,
    DECISION_REVIEW,
    assess_batch,
    assess_scan,
)


def setup_function(_):
    config.PROVIDER_MODE = "local"  # mock 분류


def test_scan_local_is_review_not_auto():
    # 로컬 mock 분류는 확신 low → 자동확정 금지, 사람 확인 등급
    res = assess_scan(b"fake-image")
    assert res["decision"] == DECISION_REVIEW
    assert res["category"] in ("other", "irrelevant")


def test_batch_groups_and_recommends():
    images = [("a.jpg", b"x"), ("b.jpg", b"y"), ("c.png", b"z")]
    out = assess_batch(images)
    assert len(out["candidates"]) == 3
    # summary 합 == 입력 수
    assert sum(out["summary"].values()) == 3
    # recommended 는 rejected 제외 목록
    rejected = [c["file_name"] for c in out["candidates"] if c["decision"] == DECISION_REJECT]
    assert set(out["recommended"]) == {"a.jpg", "b.jpg", "c.png"} - set(rejected)


def test_batch_empty():
    out = assess_batch([])
    assert out["candidates"] == []
    assert out["recommended"] == []
