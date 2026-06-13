"""Pure proportional-split math and structured split builder. No UI, no I/O."""

from decimal import Decimal
from functools import reduce
from math import gcd


def _largest_remainder(total: int, weights: dict) -> dict:
    """
    Split `total` (integer AMD) among keys proportionally to their weights.
    Uses the largest-remainder method so sum(result) == total always.
    """
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        return {k: 0 for k in weights}
    raw = {k: Decimal(total) * Decimal(str(v)) / Decimal(str(weight_sum))
           for k, v in weights.items()}
    floored = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(floored.values())
    for k, _ in sorted(raw.items(), key=lambda x: -(x[1] % 1)):
        if remainder <= 0:
            break
        floored[k] += 1
        remainder -= 1
    assert sum(floored.values()) == total, "Rounding error"
    return floored


def _equal_split(names: list, total: int) -> dict:
    equal_weights = {n: 1 for n in names}
    return _largest_remainder(total, equal_weights)


def _pct_split(pct_dict: dict, total: int) -> dict:
    """pct_dict: {name: float_pct}. Must sum to 100."""
    return _largest_remainder(total, pct_dict)
