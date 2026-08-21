import os
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import sys_path  # noqa: F401
from ..services import env_store, manual_adapter, session_store, split_adapter, yc_adapter
from ..services.session_view import to_view as _session_view

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionBody(BaseModel):
    kind: Literal["yc", "manual"]
    order_id: str | None = None
    session_name: str | None = None


class RosterBody(BaseModel):
    temp_participants: list[str] = []


class ManualItemBody(BaseModel):
    name: str
    price: float
    service_raw: str = ""


class ImportItem(BaseModel):
    name: str
    price: float
    service: float | str | None = None


class ImportItemsBody(BaseModel):
    items: list[ImportItem]


class AssignBody(BaseModel):
    mode: Literal["equal", "percentage", "amount", "part"]
    selected: list[str]
    values: dict[str, float] = {}


def _default_participants() -> list[str]:
    env_store.reload()
    raw = env_store.get("DEFAULT_PARTICIPANTS", "Me") or "Me"
    return [p.strip() for p in raw.split(",") if p.strip()]


@router.post("")
def create_session(body: CreateSessionBody):
    if body.kind == "yc":
        if not body.order_id:
            raise HTTPException(status_code=422, detail="order_id is required for kind=yc.")
        order = yc_adapter.load_cached_order(body.order_id)
        items = [it for it in order["items"]]
        session = session_store.create(kind="yc", order_id=body.order_id, order=order, items=items)
    else:
        session_name = (body.session_name or "").strip() or "manual"
        session = session_store.create(kind="manual", session_name=session_name, items=[])

    session.participants = _default_participants()
    return _session_view(session)


@router.get("/{session_id}")
def get_session(session_id: str):
    return _session_view(session_store.get(session_id))


@router.post("/{session_id}/roster")
def set_roster(session_id: str, body: RosterBody):
    session = session_store.get(session_id)
    defaults = _default_participants()
    temp = [p.strip() for p in body.temp_participants if p.strip()]
    session.participants = defaults + temp
    return _session_view(session)


@router.post("/{session_id}/items")
def add_manual_item(session_id: str, body: ManualItemBody):
    session = session_store.get(session_id)
    if session.kind != "manual":
        raise HTTPException(status_code=400, detail="Items can only be added directly for manual sessions.")
    price = int(round(body.price))
    service = manual_adapter.parse_service(body.service_raw, price)
    net_price = price + service
    session.items.append({
        "name": body.name.strip() or f"Item {len(session.items) + 1}",
        "price": price,
        "service": service,
        "net_price": net_price,
        "is_canceled": False,
    })
    return _session_view(session)


@router.post("/{session_id}/items/import")
def import_manual_items(session_id: str, body: ImportItemsBody):
    """
    Bulk-add items from AI-extracted receipt JSON (see /api/receipt-prompt for
    the exact prompt users are given to copy into any AI). Reuses the same
    parse_service()/net_price math as the single-item add — no new
    calculation logic, just a batched version of add_manual_item.
    """
    session = session_store.get(session_id)
    if session.kind != "manual":
        raise HTTPException(status_code=400, detail="Items can only be imported for manual sessions.")
    if not body.items:
        raise HTTPException(status_code=422, detail="No items found in that JSON — check it has an \"items\" array.")

    new_entries = []
    for i, item in enumerate(body.items):
        if not item.name or not item.name.strip():
            raise HTTPException(status_code=422, detail=f"Item {i + 1} is missing a name.")
        if item.price is None or item.price < 0:
            raise HTTPException(status_code=422, detail=f"Item {i + 1} (\"{item.name}\") has an invalid price.")
        price = int(round(item.price))
        service_raw = "" if item.service is None else str(item.service)
        try:
            service = manual_adapter.parse_service(service_raw, price)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Item {i + 1} (\"{item.name}\") has an invalid service value: {item.service!r}.",
            )
        new_entries.append({
            "name": item.name.strip(),
            "price": price,
            "service": service,
            "net_price": price + service,
            "is_canceled": False,
        })

    session.items.extend(new_entries)
    return _session_view(session)


@router.delete("/{session_id}/items/{index}")
def remove_manual_item(session_id: str, index: int):
    session = session_store.get(session_id)
    if session.kind != "manual":
        raise HTTPException(status_code=400, detail="Items can only be removed directly for manual sessions.")
    if index < 0 or index >= len(session.items):
        raise HTTPException(status_code=404, detail="Item index out of range.")
    session.items.pop(index)
    session.assigned = {}  # indices shifted — force re-assignment, mirrors starting the loop fresh
    return _session_view(session)


@router.get("/{session_id}/items/{index}")
def get_item(session_id: str, index: int):
    session = session_store.get(session_id)
    active = session.active_items()
    if index < 0 or index >= len(active):
        raise HTTPException(status_code=404, detail="Item index out of range.")
    return {
        "index": index,
        "total": len(active),
        "item": active[index],
        "participants": session.participants,
        "current_assignment": session.assigned.get(str(index)),
    }


@router.post("/{session_id}/items/{index}/assign")
def assign_item(session_id: str, index: int, body: AssignBody):
    session = session_store.get(session_id)
    active = session.active_items()
    if index < 0 or index >= len(active):
        raise HTTPException(status_code=404, detail="Item index out of range.")
    if not session.participants:
        raise HTTPException(status_code=422, detail="Set up the roster before assigning items.")

    net_price = active[index]["net_price"]
    try:
        result = split_adapter.assign_item(body.mode, body.selected, body.values, net_price, session.participants)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    session.assigned[str(index)] = result
    next_index = index + 1 if index + 1 < len(active) else None
    return {
        "index": index,
        "result": result,
        "next_index": next_index,
        "all_assigned": session.is_fully_assigned(),
    }


@router.get("/{session_id}/review")
def review(session_id: str):
    session = session_store.get(session_id)
    active = session.active_items()
    rows = []
    for i, item in enumerate(active):
        rec = session.assigned.get(str(i))
        rows.append({"index": i, "item": item, "assignment": rec})
    return {"items": rows, "all_assigned": session.is_fully_assigned()}


@router.post("/{session_id}/finish")
def finish(session_id: str):
    session = session_store.get(session_id)
    if not session.is_fully_assigned():
        raise HTTPException(status_code=422, detail="Every item must be assigned before finishing.")

    assigned_items = session.assembled_items()

    if session.kind == "yc":
        fees = {
            "delivery_fee": session.order["delivery_fee"],
            "service_fee": session.order["service_fee"],
            "driver_tip": session.order["driver_tip"],
        }
        order_total = session.order["total_to_pay"]
    else:
        fees = {"delivery_fee": 0, "service_fee": 0, "driver_tip": 0}
        order_total = sum(it["net_price"] for it in assigned_items)

    result = split_adapter.finish(session.participants, assigned_items, fees)
    session.fee_allocations = result["fee_allocations"]
    session.totals = result["totals"]

    grand = sum(t["total"] for t in session.totals.values())
    discrepancy = abs(grand - order_total)

    return {
        "fee_allocations": session.fee_allocations,
        "totals": session.totals,
        "grand_total": grand,
        "order_total": order_total,
        "discrepancy": discrepancy,
        "discrepancy_warning": discrepancy > 2,
    }
