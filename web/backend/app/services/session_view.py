"""Shared serialization of SplitSession -> API response dict, used by both
the sessions router and the history "edit" endpoint."""

from ..models.session import SplitSession


def to_view(s: SplitSession) -> dict:
    active = s.active_items()
    return {
        "session_id": s.session_id,
        "kind": s.kind,
        "order_id": s.order_id,
        "session_name": s.session_name,
        "order": s.order,
        "participants": s.participants,
        "items": s.items,
        "active_item_count": len(active),
        "assigned_count": len(s.assigned),
        "fee_allocations": s.fee_allocations,
        "totals": s.totals,
        "currency": s.currency,
        "saved_path": s.saved_path,
    }
