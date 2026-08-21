"""Thin wrapper over split_math.build_split / split_basket.allocate_fees /
compute_totals. No calculation logic lives here — this only shapes
request/response data around the unchanged functions."""

from .. import sys_path  # noqa: F401

from split_math import build_split  # noqa: E402
from split_basket import allocate_fees, compute_totals  # noqa: E402


def assign_item(mode: str, selected: list, values: dict, net_price: int, participants: list) -> dict:
    """Raises ValueError (caller maps to HTTP 422) exactly as the CLI does."""
    amounts, weights, method = build_split(mode, selected, values, net_price, participants)
    return {
        "assignments": amounts,
        "assignment_weights": weights,
        "split_method": method,
    }


def finish(participants: list, assigned_items: list, fees: dict) -> dict:
    """fees: {delivery_fee, service_fee, driver_tip} (order-shaped keys)."""
    item_totals = {
        p: sum(it["assignments"].get(p, 0) for it in assigned_items)
        for p in participants
    }
    order_like = {
        "delivery_fee": fees.get("delivery_fee", 0),
        "service_fee": fees.get("service_fee", 0),
        "driver_tip": fees.get("driver_tip", 0),
    }
    fee_allocations = allocate_fees(participants, item_totals, order_like)
    totals = compute_totals(participants, assigned_items, fee_allocations)
    return {"fee_allocations": fee_allocations, "totals": totals}
