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


def build_split(mode: str, selected: list, values: dict,
                net_price: int, participants: list) -> tuple:
    """
    Turn a structured selection into (amounts, weights, method).

    mode         : "equal" | "percentage" | "amount" | "part"
    selected     : participants sharing this item (subset of `participants`)
    values       : {participant: number} for non-equal modes (keys cover `selected`)
    net_price    : item net price in integer AMD
    participants : full active roster (used to zero-fill display weights)

    Output mirrors the legacy parse_assignment contract:
      amounts : {participant: int} over the sharing people, summing to net_price
      weights : {participant: number} zero-filled across the full roster
      method  : label string for the report
    """
    # Canonical order + dedupe against the roster.
    selected = [p for p in participants if p in set(selected)]
    if not selected:
        raise ValueError("Select at least one person for this item.")

    if mode == "equal":
        amounts = _equal_split(selected, net_price)
        weights = {p: (1 if p in selected else 0) for p in participants}
        if len(selected) == len(participants):
            method = "equal/all"
        elif len(selected) == 1:
            method = "single"
        else:
            method = "equal/partial"
        return amounts, weights, method

    missing = [p for p in selected if p not in values]
    if missing:
        raise ValueError(f"Missing value for: {', '.join(missing)}")

    if mode == "percentage":
        pct_sum = sum(float(values[p]) for p in selected)
        if abs(pct_sum - 100) > 0.01:
            raise ValueError(f"Percentages sum to {pct_sum:.1f}%, must be 100%.")
        pct_map = {p: float(values[p]) for p in selected}
        amounts = _pct_split(pct_map, net_price)
        weights = {p: round(float(values[p]), 2) if p in selected else 0
                   for p in participants}
        return amounts, weights, "percentage"

    if mode == "amount":
        amounts_in = {p: int(round(float(values[p]))) for p in selected}
        total = sum(amounts_in.values())
        if total != net_price:
            raise ValueError(
                f"Amounts sum to {total:,} AMD, but item net price is "
                f"{net_price:,} AMD.")
        nonzero = [v for v in amounts_in.values() if v > 0]
        g = reduce(gcd, nonzero) if nonzero else 1
        weights = {p: amounts_in.get(p, 0) // g for p in participants}
        return amounts_in, weights, "fixed"

    if mode == "part":
        parts = {p: float(values[p]) for p in selected}
        if sum(parts.values()) <= 0:
            raise ValueError("Parts must be positive numbers.")
        amounts = _largest_remainder(net_price, parts)
        int_parts = {p: int(round(float(values[p]))) for p in selected}
        nonzero = [v for v in int_parts.values() if v > 0]
        g = reduce(gcd, nonzero) if nonzero else 1
        weights = {p: int_parts.get(p, 0) // g for p in participants}
        return amounts, weights, "ratio"

    raise ValueError(f"Unknown split mode: {mode}")
