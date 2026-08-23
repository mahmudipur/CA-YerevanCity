"""
Regression test: an order cached before the `image` field was added to
_build_order must be treated as stale and re-fetched, not silently served
without pictures.
"""

import json

import pytest

from conftest import TEST_TELEGRAM_ID
from app.config import TMP_DIR
from app.services import yc_adapter
from app.services.user_store import AuthedUser

ORDER_ID = "STALE_CACHE_TEST"

FAKE_USER = AuthedUser(
    telegram_id=TEST_TELEGRAM_ID,
    telegram_username=None,
    first_name="Test",
    last_name=None,
    photo_url=None,
    default_participants="Me",
    google_sheet_id=None,
    yc_phone_local="",
    yc_phone_e164="",
    yc_device_id="",
    yc_jwt="fake-jwt",
)


@pytest.fixture
def old_shaped_cache():
    """An order cache written before `image` existed — no `image` key at all."""
    order = {
        "order_id": ORDER_ID,
        "create_date": "2026-01-01T00:00:00",
        "finish_date": None,
        "status": 7,
        "status_label": "Delivered",
        "is_delivery": False,
        "payment_method": 2,
        "payment_label": "Card",
        "branch_address": "x",
        "total_price": 1000,
        "total_to_pay": 1000,
        "delivery_fee": 0,
        "service_fee": 0,
        "driver_tip": 0,
        "items": [
            {"id": "1", "name": "Old Item", "quantity": 1.0, "unit": None, "unit_price": 1000,
             "total_price": 1000, "discount": 0, "net_price": 1000, "is_canceled": False},
        ],
    }
    path = TMP_DIR / f"order_{TEST_TELEGRAM_ID}_{ORDER_ID}.json"
    path.write_text(json.dumps(order))
    yield path
    path.unlink(missing_ok=True)


def test_pre_image_field_cache_is_treated_as_stale(old_shaped_cache, monkeypatch):
    refetched = {"called": False}

    def fake_get_order_detail(token, order_id, created_on):
        refetched["called"] = True
        return {"orderItems": [{"id": 1, "name": "Old Item", "price": 1000, "quantity": 1,
                                 "totalPrice": 1000, "discount": 0, "isCanceled": False,
                                 "photo": "https://example.com/photo.png"}]}

    def fake_get_orders(token, page=1, count=20):
        return [{"offlineOrderId": ORDER_ID, "createDate": "2026-01-01T00:00:00", "totalToPay": 1000,
                 "userDeliveryFee": 0, "serviceFee": 0, "driverTipAmount": 0, "status": 7,
                 "isDelivery": False, "paymentMethod": 2, "branchAddress": {"address": "x"}}]

    monkeypatch.setattr(yc_adapter, "get_order_detail", fake_get_order_detail)
    monkeypatch.setattr(yc_adapter, "get_orders", fake_get_orders)

    order = yc_adapter.fetch_and_cache_order(FAKE_USER, order_id=ORDER_ID, refresh=False)

    assert refetched["called"], "stale (pre-image-field) cache should have triggered a re-fetch"
    assert order["items"][0]["image"] == "https://example.com/photo.png"
