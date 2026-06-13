import pytest
from split_math import build_split

P = ["Me", "Mahdi", "Amir"]


def test_equal_all():
    amounts, weights, method = build_split("equal", P, {}, 1500, P)
    assert sum(amounts.values()) == 1500
    assert weights == {"Me": 1, "Mahdi": 1, "Amir": 1}
    assert method == "equal/all"


def test_equal_partial():
    amounts, weights, method = build_split("equal", ["Me", "Amir"], {}, 1000, P)
    assert amounts == {"Me": 500, "Amir": 500}
    assert weights == {"Me": 1, "Mahdi": 0, "Amir": 1}
    assert method == "equal/partial"


def test_single():
    amounts, weights, method = build_split("equal", ["Me"], {}, 800, P)
    assert amounts == {"Me": 800}
    assert weights == {"Me": 1, "Mahdi": 0, "Amir": 0}
    assert method == "single"


def test_percentage():
    amounts, weights, method = build_split(
        "percentage", ["Me", "Amir"], {"Me": 67, "Amir": 33}, 1500, P)
    assert sum(amounts.values()) == 1500
    assert weights == {"Me": 67, "Mahdi": 0, "Amir": 33}
    assert method == "percentage"


def test_percentage_bad_sum():
    with pytest.raises(ValueError, match="100"):
        build_split("percentage", ["Me", "Amir"], {"Me": 60, "Amir": 30}, 1500, P)


def test_amount():
    amounts, weights, method = build_split(
        "amount", ["Me", "Amir"], {"Me": 1000, "Amir": 500}, 1500, P)
    assert amounts == {"Me": 1000, "Amir": 500}
    assert weights == {"Me": 2, "Mahdi": 0, "Amir": 1}
    assert method == "fixed"


def test_amount_bad_sum():
    with pytest.raises(ValueError, match="net price"):
        build_split("amount", ["Me", "Amir"], {"Me": 1000, "Amir": 400}, 1500, P)


def test_part_ratio():
    amounts, weights, method = build_split(
        "part", ["Me", "Amir"], {"Me": 2, "Amir": 1}, 1500, P)
    assert amounts == {"Me": 1000, "Amir": 500}
    assert weights == {"Me": 2, "Mahdi": 0, "Amir": 1}
    assert method == "ratio"


def test_part_equivalent_ratios():
    a1, w1, _ = build_split("part", ["Me", "Amir"], {"Me": 4, "Amir": 2}, 1500, P)
    assert a1 == {"Me": 1000, "Amir": 500}
    assert w1 == {"Me": 2, "Mahdi": 0, "Amir": 1}


def test_empty_selection():
    with pytest.raises(ValueError, match="[Ss]elect"):
        build_split("equal", [], {}, 100, P)


def test_missing_value():
    with pytest.raises(ValueError, match="[Mm]issing"):
        build_split("amount", ["Me", "Amir"], {"Me": 1000}, 1500, P)
