"""Reconstructs an editable SplitSession from a previously saved split_*.json,
so a past split can be re-opened, tweaked, and re-saved over the same file."""

from fastapi import HTTPException

from ..config import TMP_DIR
from . import persistence, session_store
from .persistence import scoped_id

ASSIGNMENT_KEYS = ("assignments", "assignment_weights", "split_method")


def start_edit(user_id: int, split_id: str):
    split = persistence.load_split(user_id, split_id)
    is_manual = "session_name" in split

    raw_items = []
    assigned = {}
    for i, it in enumerate(split.get("items", [])):
        raw = {k: v for k, v in it.items() if k not in ASSIGNMENT_KEYS}
        raw_items.append(raw)
        if all(k in it for k in ASSIGNMENT_KEYS):
            assigned[str(i)] = {k: it[k] for k in ASSIGNMENT_KEYS}

    if is_manual:
        session = session_store.create(
            user_id,
            kind="manual",
            session_name=split.get("session_name", split_id),
            items=raw_items,
        )
    else:
        order = _reconstruct_order(user_id, split_id, split)
        session = session_store.create(
            user_id,
            kind="yc",
            order_id=split_id,
            order=order,
            items=raw_items,
        )

    session.participants = list(split.get("participants", []))
    session.assigned = assigned
    session.fee_allocations = split.get("fee_allocations")
    session.totals = split.get("totals")
    session.currency = split.get("currency")
    session.saved_path = str(TMP_DIR / f"split_{scoped_id(user_id, split_id)}.json")
    return session


def _reconstruct_order(user_id: int, split_id: str, split: dict) -> dict:
    """Prefer the real cached order_{id}.json (exact original shape); fall
    back to rebuilding the fields split_basket.py's output actually needs
    from the split JSON itself if the order cache is missing."""
    cached_path = TMP_DIR / f"order_{scoped_id(user_id, split_id)}.json"
    if cached_path.exists():
        import json
        return json.loads(cached_path.read_text())

    meta = split.get("order_meta", {})
    fees = split.get("fees", {})
    raise_if_missing = HTTPException(
        status_code=404,
        detail=f"Order cache not found for {split_id} — can't fully reconstruct order details for editing.",
    )
    if not meta:
        raise raise_if_missing
    return {
        "order_id": split_id,
        "create_date": meta.get("create_date"),
        "finish_date": meta.get("create_date"),
        "status": None,
        "status_label": meta.get("status_label", ""),
        "is_delivery": meta.get("is_delivery", False),
        "payment_method": None,
        "payment_label": meta.get("payment_label", ""),
        "branch_address": meta.get("branch_address", ""),
        "total_price": split.get("order_total", 0),
        "total_to_pay": split.get("order_total", 0),
        "delivery_fee": fees.get("delivery", 0),
        "service_fee": fees.get("service", 0),
        "driver_tip": fees.get("driver_tip", 0),
        "items": split.get("items", []),
    }
