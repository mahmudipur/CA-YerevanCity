"""
Golden-value tests pinning split_basket.compute_revolut_currency — the pure
helper extracted from collect_payment_info() — so any future change to the
Revolut fee/distribution math is caught immediately.
"""

from split_basket import compute_revolut_currency

TOTALS = {"Alice": {"total": 6000}, "Bob": {"total": 3000}, "Carol": {"total": 1000}}
PARTICIPANTS = ["Alice", "Bob", "Carol"]


def test_weekend_and_fair_usage_fees_stack():
    result = compute_revolut_currency(411.5, 25.0, True, True, TOTALS, PARTICIPANTS)
    assert result == {
        "method": "revolut",
        "rate": 411.5,
        "eur_paid": 25.0,
        "is_weekend": True,
        "eur_fee": 0.25,
        "is_fair_usage": True,
        "eur_fair_usage_fee": 0.25,
        "eur_effective": 25.5,
        "eur_per_person": {"Alice": 15.3, "Bob": 7.65, "Carol": 2.55},
    }


def test_no_fees():
    result = compute_revolut_currency(400.0, 10.0, False, False, TOTALS, PARTICIPANTS)
    assert result == {
        "method": "revolut",
        "rate": 400.0,
        "eur_paid": 10.0,
        "is_weekend": False,
        "eur_fee": 0.0,
        "is_fair_usage": False,
        "eur_fair_usage_fee": 0.0,
        "eur_effective": 10.0,
        "eur_per_person": {"Alice": 6.0, "Bob": 3.0, "Carol": 1.0},
    }


def test_eur_per_person_sums_to_effective_total():
    result = compute_revolut_currency(350.25, 17.37, True, False, TOTALS, PARTICIPANTS)
    assert round(sum(result["eur_per_person"].values()), 2) == round(result["eur_effective"], 2)


def test_zero_total_amd_gives_zero_shares():
    zero_totals = {p: {"total": 0} for p in PARTICIPANTS}
    result = compute_revolut_currency(400.0, 5.0, False, False, zero_totals, PARTICIPANTS)
    assert result["eur_per_person"] == {"Alice": 0.0, "Bob": 0.0, "Carol": 0.0}
