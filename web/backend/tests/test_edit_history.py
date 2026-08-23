"""Proves a saved split can be re-opened for editing, have one item's split
changed, and re-saved to the SAME split_{id}.json (not a duplicate)."""

import json

import pytest

from conftest import TEST_TELEGRAM_ID

from app.config import TMP_DIR

SPLIT_ID = "edit_smoke_cafe"  # must equal slugify(session_name) below — that's the real invariant manual_split.py relies on
_SCOPED = f"{TEST_TELEGRAM_ID}_{SPLIT_ID}"


@pytest.fixture
def sample_manual_split():
    participants = ["Alice", "Bob"]
    items = [
        {"name": "Coffee", "price": 1000, "service": 0, "net_price": 1000, "is_canceled": False,
         "assignments": {"Alice": 500, "Bob": 500}, "assignment_weights": {"Alice": 1, "Bob": 1}, "split_method": "equal/all"},
        {"name": "Cake", "price": 2000, "service": 0, "net_price": 2000, "is_canceled": False,
         "assignments": {"Alice": 2000, "Bob": 0}, "assignment_weights": {"Alice": 1, "Bob": 0}, "split_method": "single"},
    ]
    totals = {"Alice": {"items": 2500, "fees": 0, "total": 2500}, "Bob": {"items": 500, "fees": 0, "total": 500}}
    split_data = {
        "session_name": "Edit Smoke Cafe",
        "order_id": SPLIT_ID,
        "split_date": "2026-01-01T00:00:00+00:00",
        "participants": participants,
        "items": items,
        "fees": {"delivery": 0, "service": 0, "driver_tip": 0},
        "fee_allocations": {p: {"delivery": 0, "service": 0, "driver_tip": 0, "total": 0} for p in participants},
        "totals": totals,
        "currency": {"method": "cash"},
        "order_total": 3000,
        "order_meta": {"create_date": "2026-01-01", "status_label": "Manual", "branch_address": "Edit Smoke Cafe",
                       "payment_label": "Cash", "is_delivery": False},
    }
    path = TMP_DIR / f"split_{_SCOPED}.json"
    path.write_text(json.dumps(split_data))
    yield split_data
    path.unlink(missing_ok=True)


def test_edit_and_resave_overwrites_same_file(sample_manual_split, authed_client):
    client = authed_client

    edit_resp = client.post(f"/api/history/{SPLIT_ID}/edit")
    assert edit_resp.status_code == 200, edit_resp.text
    session = edit_resp.json()
    assert session["kind"] == "manual"
    assert session["participants"] == ["Alice", "Bob"]
    assert session["session_name"] == "Edit Smoke Cafe"
    session_id = session["session_id"]

    # Re-assign the "Cake" item (index 1) to be equal between both instead of Alice-only.
    resp = client.post(
        f"/api/sessions/{session_id}/items/1/assign",
        json={"mode": "equal", "selected": ["Alice", "Bob"], "values": {}},
    )
    assert resp.status_code == 200, resp.text

    finish_resp = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_resp.status_code == 200, finish_resp.text

    pay_resp = client.post(f"/api/sessions/{session_id}/payment", json={"method": "cash"})
    assert pay_resp.status_code == 200

    save_resp = client.post(f"/api/sessions/{session_id}/save")
    assert save_resp.status_code == 200, save_resp.text
    saved = save_resp.json()

    # Same split id/file, not a new one.
    assert saved["split_id"] == SPLIT_ID
    assert saved["saved_path"] == str(TMP_DIR / f"split_{_SCOPED}.json")

    on_disk = json.loads((TMP_DIR / f"split_{_SCOPED}.json").read_text())
    assert on_disk["totals"]["Alice"]["total"] == 1500  # 500 (coffee) + 1000 (cake half)
    assert on_disk["totals"]["Bob"]["total"] == 1500
    assert len(list(TMP_DIR.glob(f"split_{_SCOPED}*.json"))) == 1
