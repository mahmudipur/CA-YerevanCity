"""Smoke test: the image export endpoint calls the real, unmodified
generate_receipt_image.py logic against a split JSON and produces a valid
PNG covering every row (the CSV/screenshot replacement — see the service's
docstring for why this exists)."""

import json

import pytest
from PIL import Image

from conftest import TEST_USER_ID, load_fixture_order

from app.config import TMP_DIR

SPLIT_ID = "IMAGE_SMOKE"
_SCOPED = f"{TEST_USER_ID}_{SPLIT_ID}"


@pytest.fixture
def sample_split():
    order = load_fixture_order()
    active = [it for it in order["items"] if not it["is_canceled"]]
    participants = ["Alice", "Bob"]
    items = []
    for it in active:
        weights = {"Alice": 1, "Bob": 1}
        from split_math import _equal_split
        amounts = _equal_split(participants, it["net_price"])
        items.append({**it, "assignments": amounts, "assignment_weights": weights, "split_method": "equal/all"})
    totals = {p: {"items": sum(i["assignments"][p] for i in items), "fees": 0,
                  "total": sum(i["assignments"][p] for i in items)} for p in participants}
    split_data = {
        "session_name": "Image Smoke",
        "order_id": SPLIT_ID,
        "split_date": "2026-01-01T00:00:00+00:00",
        "participants": participants,
        "items": items,
        "fees": {"delivery": 0, "service": 0, "driver_tip": 0},
        "fee_allocations": {p: {"delivery": 0, "service": 0, "driver_tip": 0, "total": 0} for p in participants},
        "totals": totals,
        "currency": {"method": "cash"},
        "order_total": sum(i["net_price"] for i in items),
        "order_meta": {"create_date": "2026-01-01", "status_label": "Delivered", "branch_address": "x",
                       "payment_label": "Card", "is_delivery": False},
    }
    path = TMP_DIR / f"split_{_SCOPED}.json"
    path.write_text(json.dumps(split_data))
    yield split_data
    path.unlink(missing_ok=True)
    (TMP_DIR / f"receipt_{_SCOPED}.png").unlink(missing_ok=True)


def test_image_download_is_a_valid_png_covering_every_row(sample_split, authed_client):
    resp = authed_client.get(f"/api/sessions/{SPLIT_ID}/image")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"

    out_path = TMP_DIR / f"receipt_{_SCOPED}.png"
    img = Image.open(out_path)
    assert img.format == "PNG"
    # One image, tall enough to hold every item row + totals — never
    # requires scrolling regardless of item count (the whole point).
    min_expected_height = 40 * (len(sample_split["items"]) + 3)
    assert img.height >= min_expected_height
