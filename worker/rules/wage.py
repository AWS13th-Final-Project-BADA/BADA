"""급여-입금 차액 — 규칙 기반(설명 가능). LLM 사용 금지.

기대급여 = 시급 × 확인된 근무시간 합
실수령   = 입금내역 합
미지급_의심 = 기대급여 − 실수령   (← '의심'으로만 표기, '확정' 금지)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WageResult:
    total_expected_wage: int | None
    total_received_wage: int
    suspected_unpaid: int | None
    calculation_detail: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def compute_unpaid(
    agreed_hourly_wage: int | None,
    worked_hours: list[float],
    deposits: list[int],
) -> WageResult:
    received = sum(deposits)
    notes: list[str] = []

    if not agreed_hourly_wage or not worked_hours:
        # 근무시간/시급 불확실 → 차액 계산하지 않고 누락 안내로 넘긴다.
        notes.append("근무시간 또는 약속 시급이 불충분하여 차액을 계산하지 않았습니다. 확인이 필요합니다.")
        return WageResult(
            total_expected_wage=None,
            total_received_wage=received,
            suspected_unpaid=None,
            calculation_detail={"hours_sum": sum(worked_hours), "hourly_wage": agreed_hourly_wage},
            notes=notes,
        )

    hours_sum = sum(worked_hours)
    expected = int(round(agreed_hourly_wage * hours_sum))
    suspected = expected - received
    if suspected < 0:
        notes.append("입금액이 기대급여보다 큽니다. 추가 항목(수당 등) 확인이 필요합니다.")

    return WageResult(
        total_expected_wage=expected,
        total_received_wage=received,
        suspected_unpaid=suspected,
        calculation_detail={
            "hourly_wage": agreed_hourly_wage,
            "hours_sum": hours_sum,
            "expected": expected,
            "received": received,
            "formula": "expected = hourly_wage * hours_sum; suspected = expected - received",
        },
        notes=notes,
    )
