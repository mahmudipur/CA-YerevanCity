from split_math import _largest_remainder, _equal_split, _pct_split


def test_largest_remainder_sums_to_total():
    out = _largest_remainder(694, {"a": 1, "b": 1, "c": 1})
    assert sum(out.values()) == 694
    assert sorted(out.values()) == [231, 231, 232]


def test_largest_remainder_zero_weights():
    assert _largest_remainder(100, {"a": 0, "b": 0}) == {"a": 0, "b": 0}


def test_equal_split_sums_to_total():
    out = _equal_split(["a", "b"], 1500)
    assert out == {"a": 750, "b": 750}


def test_pct_split_proportional():
    out = _pct_split({"a": 60.0, "b": 40.0}, 1000)
    assert out == {"a": 600, "b": 400}
    assert sum(out.values()) == 1000
