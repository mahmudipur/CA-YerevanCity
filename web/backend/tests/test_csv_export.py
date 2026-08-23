"""Smoke test: the export endpoint calls the real, unmodified generate_csv.py
logic against a split JSON and produces a readable CSV."""

import csv
import json

import pytest

from conftest import TEST_TELEGRAM_ID, load_fixture_order

from app.config import TMP_DIR

SPLIT_ID = "CSV_SMOKE"
_SCOPED = f"{TEST_TELEGRAM_ID}_{SPLIT_ID}"


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
    (TMP_DIR / f"report_{_SCOPED}.csv").unlink(missing_ok=True)


def test_csv_download_produces_expected_rows(sample_split, authed_client):
    resp = authed_client.get(f"/api/sessions/{SPLIT_ID}/csv")
    assert resp.status_code == 200
    text = resp.text.lstrip("﻿")
    rows = list(csv.reader(text.splitlines()))
    assert rows[0][:3] == ["product", "price", "services"]
    item_names = [r[0] for r in rows[1:1 + len(sample_split["items"])]]
    assert item_names == [it["name"] for it in sample_split["items"]]
