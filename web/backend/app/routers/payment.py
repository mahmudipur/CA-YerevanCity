from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import payment_service, persistence, session_store

router = APIRouter(prefix="/api/sessions", tags=["payment"])


class PaymentBody(BaseModel):
    method: Literal["cash", "revolut"]
    rate: float | None = None
    eur_paid: float | None = None
    is_weekend: bool = False
    is_fair_usage: bool = False


@router.post("/{session_id}/payment")
def set_payment(session_id: str, body: PaymentBody):
    session = session_store.get(session_id)
    if session.totals is None:
        raise HTTPException(status_code=422, detail="Finish assigning items before setting payment info.")

    if body.method == "cash":
        session.currency = payment_service.cash()
        return session.currency

    if body.rate is None or body.rate <= 0:
        raise HTTPException(status_code=422, detail="Enter a positive EUR → AMD rate.")
    if body.eur_paid is None or body.eur_paid <= 0:
        raise HTTPException(status_code=422, detail="Enter a positive EUR amount paid.")

    session.currency = payment_service.revolut(
        body.rate, body.eur_paid, body.is_weekend, body.is_fair_usage,
        session.totals, session.participants,
    )
    return session.currency


@router.post("/{session_id}/save")
def save(session_id: str):
    session = session_store.get(session_id)
    if session.totals is None or session.currency is None:
        raise HTTPException(status_code=422, detail="Finish the split and set payment info before saving.")

    assigned_items = session.assembled_items()
    split_date = persistence.now_iso()

    if session.kind == "yc":
        order = session.order
        split_id = session.order_id
        fees = {"delivery": order["delivery_fee"], "service": order["service_fee"], "driver_tip": order["driver_tip"]}
        order_total = order["total_to_pay"]
        order_meta = {
            "create_date": order.get("create_date"),
            "status_label": order.get("status_label"),
            "branch_address": order.get("branch_address"),
            "payment_label": order.get("payment_label"),
            "is_delivery": order.get("is_delivery"),
        }
        split_data = {
            "order_id": split_id,
            "split_date": split_date,
            "participants": session.participants,
            "items": assigned_items,
            "fees": fees,
            "fee_allocations": session.fee_allocations,
            "totals": session.totals,
            "currency": session.currency,
            "order_total": order_total,
            "order_meta": order_meta,
        }
    else:
        from ..services import manual_adapter
        slug = manual_adapter.slugify(session.session_name)
        split_id = slug
        empty_fees = {"delivery": 0, "service": 0, "driver_tip": 0}
        order_total = sum(it["net_price"] for it in assigned_items)
        split_data = {
            "session_name": session.session_name,
            "order_id": slug,
            "split_date": split_date,
            "participants": session.participants,
            "items": assigned_items,
            "fees": empty_fees,
            "fee_allocations": session.fee_allocations,
            "totals": session.totals,
            "currency": session.currency,
            "order_total": order_total,
            "order_meta": {
                "create_date": split_date[:10],
                "status_label": "Manual",
                "branch_address": session.session_name,
                "payment_label": session.currency.get("method", "cash").capitalize(),
                "is_delivery": False,
            },
        }

    saved_path = persistence.save_split(split_id, split_data)
    session.saved_path = saved_path
    return {"split_id": split_id, "saved_path": saved_path, "split": split_data}
