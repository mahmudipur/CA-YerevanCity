"""Edit flow for a Yerevan City order split — exercises order reconstruction
from the cached order_{id}.json alongside the saved split_{id}.json."""

import json

import pytest

from conftest import TEST_TELEGRAM_ID, load_fixture_order

from app.config import TMP_DIR

ORDER_ID = "FIXTURE"
_SCOPED = f"{TEST_TELEGRAM_ID}_{ORDER_ID}"


@pytest.fixture
def cached_order_and_split():
    order = load_fixture_order()
    order_path = TMP_DIR / f"order_{_SCOPED}.json"
    order_path.write_text(json.dumps(order))

    participants = ["Alice", "Bob"]
    active = [it for it in order["items"] if not it["is_canceled"]]
    items = []
    for it in active:
        items.append({**it, "assignments": {"Alice": it["net_price"], "Bob": 0},
                      "assignment_weights": {"Alice": 1, "Bob": 0}, "split_method": "single"})
    totals = {"Alice": {"items": sum(i["net_price"] for i in active), "fees": 0, "total": sum(i["net_price"] for i in active)},
              "Bob": {"items": 0, "fees": 0, "total": 0}}
    split_data = {
        "order_id": ORDER_ID,
        "split_date": "2026-01-01T00:00:00+00:00",
        "participants": participants,
        "items": items,
        "fees": {"delivery": order["delivery_fee"], "service": order["service_fee"], "driver_tip": order["driver_tip"]},
        "fee_allocations": {p: {"delivery": 0, "service": 0, "driver_tip": 0, "total": 0} for p in participants},
        "totals": totals,
        "currency": {"method": "cash"},
        "order_total": order["total_to_pay"],
        "order_meta": {"create_date": order["create_date"], "status_label": order["status_label"],
                       "branch_address": order["branch_address"], "payment_label": order["payment_label"],
                       "is_delivery": order["is_delivery"]},
    }
    split_path = TMP_DIR / f"split_{_SCOPED}.json"
    split_path.write_text(json.dumps(split_data))
    yield split_data
    order_path.unlink(missing_ok=True)
    split_path.unlink(missing_ok=True)


def test_edit_yc_split_reconstructs_order_and_resaves(cached_order_and_split, authed_client):
    client = authed_client

    edit_resp = client.post(f"/api/history/{ORDER_ID}/edit")
    assert edit_resp.status_code == 200, edit_resp.text
    session = edit_resp.json()
    assert session["kind"] == "yc"
    assert session["order"]["order_id"] == ORDER_ID
    assert session["order"]["delivery_fee"] == 300  # from the real cached order, not a guess
    session_id = session["session_id"]

    # Re-balance item 0 to be shared equally instead of Alice-only.
    resp = client.post(
        f"/api/sessions/{session_id}/items/0/assign",
        json={"mode": "equal", "selected": ["Alice", "Bob"], "values": {}},
    )
    assert resp.status_code == 200, resp.text

    assert client.post(f"/api/sessions/{session_id}/finish").status_code == 200
    assert client.post(f"/api/sessions/{session_id}/payment", json={"method": "cash"}).status_code == 200
    save_resp = client.post(f"/api/sessions/{session_id}/save")
    assert save_resp.status_code == 200, save_resp.text
    assert save_resp.json()["split_id"] == ORDER_ID
    assert len(list(TMP_DIR.glob(f"split_{_SCOPED}*.json"))) == 1
