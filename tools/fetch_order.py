#!/usr/bin/env python3
"""
Fetch the latest Yerevan City order and cache it to .tmp/order_{id}.json

The cached JSON is the canonical input for split_basket.py.

Usage:
  python tools/fetch_order.py            # fetch latest order
  python tools/fetch_order.py --refresh  # re-fetch even if already cached
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from yc_client import YCError, get_order_detail, get_orders

ROOT    = Path(__file__).parent.parent
ENV_PATH = ROOT / ".env"
TMP_DIR  = ROOT / ".tmp"

# API timestamps (createDate/finishDate) are UTC with no offset. Yerevan City's
# GetOfflineOrderById joins line items by the LOCAL calendar date, so an order
# placed 20:00-23:59 UTC (00:00-03:59 local) is stored under the *next* day and
# returns zero items if looked up by its raw UTC date. Armenia is a fixed UTC+4
# (no DST), so convert before taking the date portion.
ARMENIA_TZ = timezone(timedelta(hours=4))

STATUS_MAP = {
    0: "Pending",
    1: "Processing",
    2: "Delivered",
    3: "Canceled",
    4: "Ready for pickup",
}

PAYMENT_MAP = {
    1: "Cash",
    2: "Card",
    3: "Bonus points",
    4: "Idram",
    5: "Online card",
}


def _load_token() -> str:
    token = os.getenv("YC_JWT", "").strip()
    if not token or token == "nothing":
        print("No JWT found. Run: python tools/auth_yc.py")
        sys.exit(1)
    return token


def _parse_date(iso_str: str | None) -> str | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        # Naive timestamps from the API are UTC; aware ones get normalized to UTC.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ARMENIA_TZ).strftime("%Y-%m-%d")
    except ValueError:
        return iso_str[:10]


def _build_order(list_item: dict, detail: dict) -> dict:
    """Merge list-level metadata with detail response into a clean order dict."""
    items = []
    for raw in detail.get("orderItems", []):
        unit_price  = int(round(float(raw.get("price", 0) or 0)))
        quantity    = float(raw.get("quantity", 1) or 1)
        total_price = int(round(float(raw.get("totalPrice", 0) or 0)))
        # Offline/pickup orders return totalPrice = 0; the `price` field is the
        # LINE total (not per-unit).  Use it directly and back-calculate unit price.
        if total_price == 0 and unit_price > 0:
            total_price = unit_price
            if quantity > 1:
                unit_price = int(round(unit_price / quantity))
        discount    = int(round(float(raw.get("discount",   0) or 0)))
        items.append({
            "id":          str(raw.get("id", "")),
            "name":        (raw.get("name") or "").strip() or f"Item {raw.get('id', '?')}",
            "quantity":    quantity,
            "unit":        raw.get("unit"),
            "unit_price":  unit_price,
            "total_price": total_price,
            "discount":    discount,
            "net_price":   total_price - discount,
            "is_canceled": bool(raw.get("isCanceled", False)),
        })

    return {
        "order_id":      list_item.get("offlineOrderId", ""),
        "create_date":   list_item.get("createDate"),
        "finish_date":   list_item.get("finishDate"),
        "status":        list_item.get("status"),
        "status_label":  STATUS_MAP.get(list_item.get("status"), str(list_item.get("status"))),
        "is_delivery":   bool(list_item.get("isDelivery", False)),
        "payment_method": list_item.get("paymentMethod"),
        "payment_label": PAYMENT_MAP.get(list_item.get("paymentMethod"), "Unknown"),
        "branch_address": (list_item.get("branchAddress") or {}).get("address", ""),
        "total_price":   int(round(float(list_item.get("totalPrice",      0) or 0))),
        "total_to_pay":  int(round(float(list_item.get("totalToPay",      0) or 0))),
        "delivery_fee":  int(round(float(list_item.get("userDeliveryFee", 0) or 0))),
        "service_fee":   int(round(float(list_item.get("serviceFee",      0) or 0))),
        "driver_tip":    int(round(float(list_item.get("driverTipAmount", 0) or 0))),
        "items":         items,
    }


def _print_summary(order: dict) -> None:
    active = [i for i in order["items"] if not i["is_canceled"]]
    canceled = len(order["items"]) - len(active)
    date = _parse_date(order["create_date"]) or "?"
    print(f"\nOrder     : {order['order_id']}")
    print(f"Date      : {date}  |  Status: {order['status_label']}")
    print(f"Branch    : {order['branch_address'] or 'N/A'}  |  Payment: {order['payment_label']}")
    print(f"Items     : {len(active)} active{f'  ({canceled} canceled)' if canceled else ''}")
    fees = []
    if order["delivery_fee"]: fees.append(f"Delivery {order['delivery_fee']:,}")
    if order["service_fee"]:  fees.append(f"Service {order['service_fee']:,}")
    if order["driver_tip"]:   fees.append(f"Tip {order['driver_tip']:,}")
    fee_str = "  |  " + "  |  ".join(fees) if fees else ""
    print(f"Total     : {order['total_to_pay']:,} AMD{fee_str}")


def main(refresh: bool = False, target_order_id: str = "") -> str:
    load_dotenv(ENV_PATH)
    token = _load_token()

    TMP_DIR.mkdir(exist_ok=True)

    if target_order_id:
        print(f"Searching for order {target_order_id} ...")
        latest = None
        for page in range(1, 20):
            try:
                batch = get_orders(token, page=page, count=20)
            except YCError as e:
                print(f"Error: {e}")
                sys.exit(1)
            if not batch:
                break
            for o in batch:
                if o.get("offlineOrderId") == target_order_id:
                    latest = o
                    break
            if latest:
                break
        if not latest:
            print(f"Order {target_order_id} not found.")
            sys.exit(1)
    else:
        print("Fetching order list ...")
        try:
            orders = get_orders(token, page=1, count=1)
        except YCError as e:
            print(f"Error: {e}")
            sys.exit(1)

        if not orders:
            print("No orders found on your account.")
            sys.exit(1)

        latest = orders[0]

    order_id   = latest.get("offlineOrderId", "")
    created_on = _parse_date(latest.get("createDate")) or ""

    if not order_id:
        print("Could not determine order ID from API response.")
        sys.exit(1)

    out_path = TMP_DIR / f"order_{order_id}.json"

    if out_path.exists() and not refresh:
        order = json.loads(out_path.read_text())
        # An empty cache is almost always stale (e.g. written before the
        # UTC→local date fix). Re-fetch instead of serving a useless result.
        if order.get("items"):
            print(f"Using cached order: {out_path}")
            _print_summary(order)
            print(f"\nNext: python tools/split_basket.py {order_id}")
            return order_id
        print(f"Cached order has no items — re-fetching {order_id} ...")

    print(f"Fetching detail for {order_id} ({created_on}) ...")
    try:
        detail = get_order_detail(token, order_id, created_on)
    except YCError as e:
        print(f"Error fetching detail: {e}")
        sys.exit(1)

    order = _build_order(latest, detail)
    out_path.write_text(json.dumps(order, indent=2, ensure_ascii=False, default=str))

    _print_summary(order)
    print(f"\nCached to: {out_path}")
    print(f"Next      : python tools/split_basket.py {order_id}")
    return order_id


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    main(refresh=refresh)
