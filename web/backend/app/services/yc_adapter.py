"""
Non-exiting adapter around fetch_order.py / yc_client.py. Reuses
_build_order, _parse_date, get_orders, get_order_detail unchanged; replaces
the CLI's print()/sys.exit() with return values and exceptions so FastAPI
routes can turn them into JSON responses.
"""

import json

from fastapi import HTTPException

from .. import sys_path  # noqa: F401
from ..config import TMP_DIR
from . import env_store
from .persistence import validate_id

from fetch_order import _build_order, _parse_date  # noqa: E402
from yc_client import YCError, get_order_detail, get_orders  # noqa: E402


def _token() -> str:
    env_store.reload()
    token = env_store.get("YC_JWT")
    if not token or token == "nothing":
        raise HTTPException(status_code=401, detail="Not signed in. Complete the Yerevan City login first.")
    return token


def list_orders(page: int = 1, count: int = 20) -> list[dict]:
    token = _token()
    try:
        return get_orders(token, page=page, count=count)
    except YCError as e:
        raise HTTPException(status_code=502, detail=str(e))


def fetch_and_cache_order(order_id: str = "", refresh: bool = False) -> dict:
    """Mirrors fetch_order.main()'s body without print()/sys.exit()."""
    token = _token()

    if order_id:
        validate_id(order_id)
        latest = None
        for page in range(1, 20):
            try:
                batch = get_orders(token, page=page, count=20)
            except YCError as e:
                raise HTTPException(status_code=502, detail=str(e))
            if not batch:
                break
            for o in batch:
                if o.get("offlineOrderId") == order_id:
                    latest = o
                    break
            if latest:
                break
        if not latest:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
    else:
        try:
            orders = get_orders(token, page=1, count=1)
        except YCError as e:
            raise HTTPException(status_code=502, detail=str(e))
        if not orders:
            raise HTTPException(status_code=404, detail="No orders found on your account.")
        latest = orders[0]

    resolved_id = latest.get("offlineOrderId", "")
    created_on = _parse_date(latest.get("createDate")) or ""
    if not resolved_id:
        raise HTTPException(status_code=502, detail="Could not determine order ID from API response.")

    out_path = TMP_DIR / f"order_{resolved_id}.json"

    if out_path.exists() and not refresh:
        order = json.loads(out_path.read_text())
        items = order.get("items")
        if items and "image" in items[0]:
            return order
        # Empty cache, or cached before the `image` field existed (older
        # cache file predating that addition to _build_order) — re-fetch
        # instead of silently serving an incomplete/stale shape.

    try:
        detail = get_order_detail(token, resolved_id, created_on)
    except YCError as e:
        raise HTTPException(status_code=502, detail=str(e))

    order = _build_order(latest, detail)
    out_path.write_text(json.dumps(order, indent=2, ensure_ascii=False, default=str))
    return order


def load_cached_order(order_id: str) -> dict:
    validate_id(order_id)
    path = TMP_DIR / f"order_{order_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Order cache not found for {order_id}.")
    return json.loads(path.read_text())
