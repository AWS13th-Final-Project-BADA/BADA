from rules.wage import compute_unpaid


def test_basic_underpayment():
    # 시급 10,320 × 174h = 1,795,680 기대 / 1,500,000 입금 → 295,680 의심
    r = compute_unpaid(10_320, [174.0], [1_500_000])
    assert r.total_expected_wage == 1_795_680
    assert r.total_received_wage == 1_500_000
    assert r.suspected_unpaid == 295_680


def test_multiple_deposits_and_hours():
    r = compute_unpaid(10_000, [80.0, 94.0], [900_000, 600_000])
    assert r.total_expected_wage == 1_740_000
    assert r.suspected_unpaid == 240_000


def test_missing_hours_does_not_calculate():
    r = compute_unpaid(10_320, [], [1_000_000])
    assert r.total_expected_wage is None
    assert r.suspected_unpaid is None
    assert r.total_received_wage == 1_000_000
    assert any("확인이 필요" in n for n in r.notes)


def test_overpaid_flags_note():
    r = compute_unpaid(10_000, [10.0], [200_000])  # 기대 100,000 < 입금 200,000
    assert r.suspected_unpaid == -100_000
    assert any("입금액이 기대급여보다" in n for n in r.notes)
