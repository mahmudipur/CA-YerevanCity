"""
Proves the web wizard produces the same split JSON (minus timestamps) as
assembling it directly from the unchanged calculation functions — i.e. the
same computation the CLI's split_basket.py performs.
"""

import json

import pytest
from fastapi.testclient import TestClient

from conftest import FIXTURE_PATH, TEST_USER_ID, load_fixture_order

from app.config import TMP_DIR
from app.main import app

ORDER_ID = "FIXTURE"
_SCOPED = f"{TEST_USER_ID}_{ORDER_ID}"
PARTICIPANTS = ["Alice", "Bob", "Carol"]

# (mode, selected, values) per active item, applied identically on both paths.
SCRIPT = [
    ("equal", PARTICIPANTS, {}),
    ("percentage", PARTICIPANTS, {"Alice": 50, "Bob": 30, "Carol": 20}),
    ("amount", ["Alice", "Bob"], {"Alice": 2000, "Bob": 1000}),
]


@pytest.fixture
def cached_order():
    order = load_fixture_order()
    path = TMP_DIR / f"order_{_SCOPED}.json"
    path.write_text(json.dumps(order))
    yield order
    path.unlink(missing_ok=True)
    (TMP_DIR / f"split_{_SCOPED}.json").unlink(missing_ok=True)


def _expected_split(order: dict) -> dict:
    """Build the split dict the exact way split_basket.py's calculation
    functions would, for the same scripted (mode, selected, values)."""
    from split_math import build_split
    from split_basket import allocate_fees, compute_totals

    active = [it for it in order["items"] if not it["is_canceled"]]
    assigned_items = []
    for item, (mode, selected, values) in zip(active, SCRIPT):
        amounts, weights, method = build_split(mode, selected, values, item["net_price"], PARTICIPANTS)
        assigned_items.append({**item, "assignments": amounts, "assignment_weights": weights, "split_method": method})

    item_totals = {p: sum(it["assignments"].get(p, 0) for it in assigned_items) for p in PARTICIPANTS}
    fee_allocs = allocate_fees(PARTICIPANTS, item_totals, order)
    totals = compute_totals(PARTICIPANTS, assigned_items, fee_allocs)

    return {
        "order_id": ORDER_ID,
        "participants": PARTICIPANTS,
        "items": assigned_items,
        "fees": {"delivery": order["delivery_fee"], "service": order["service_fee"], "driver_tip": order["driver_tip"]},
        "fee_allocations": fee_allocs,
        "totals": totals,
        "currency": {"method": "cash"},
        "order_total": order["total_to_pay"],
        "order_meta": {
            "create_date": order.get("create_date"),
            "status_label": order.get("status_label"),
            "branch_address": order.get("branch_address"),
            "payment_label": order.get("payment_label"),
            "is_delivery": order.get("is_delivery"),
        },
    }


def _strip_timestamp(split: dict) -> dict:
    return {k: v for k, v in split.items() if k != "split_date"}


def test_web_wizard_matches_direct_calculation(cached_order, authed_user_factory):
    authed_user_factory(default_participants=",".join(PARTICIPANTS))
    expected = _expected_split(cached_order)

    client = TestClient(app)

    created = client.post("/api/sessions", json={"kind": "yc", "order_id": ORDER_ID}).json()
    session_id = created["session_id"]

    client.post(f"/api/sessions/{session_id}/roster", json={"temp_participants": []})

    for i, (mode, selected, values) in enumerate(SCRIPT):
        resp = client.post(
            f"/api/sessions/{session_id}/items/{i}/assign",
            json={"mode": mode, "selected": selected, "values": values},
        )
        assert resp.status_code == 200, resp.text

    finish_resp = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_resp.status_code == 200, finish_resp.text

    pay_resp = client.post(f"/api/sessions/{session_id}/payment", json={"method": "cash"})
    assert pay_resp.status_code == 200, pay_resp.text

    save_resp = client.post(f"/api/sessions/{session_id}/save")
    assert save_resp.status_code == 200, save_resp.text
    web_split = _strip_timestamp(save_resp.json()["split"])

    assert web_split == expected
