from fastapi import APIRouter, Query

from ..services import yc_adapter

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
def list_orders(page: int = Query(1, ge=1), count: int = Query(20, ge=1, le=50)):
    raw = yc_adapter.list_orders(page=page, count=count)
    return [
        {
            "order_id": o.get("offlineOrderId"),
            "create_date": o.get("createDate"),
            "total_to_pay": o.get("totalToPay"),
            "status": o.get("status"),
            "is_delivery": o.get("isDelivery"),
        }
        for o in raw
    ]


@router.get("/latest")
def fetch_latest(refresh: bool = False):
    return yc_adapter.fetch_and_cache_order(order_id="", refresh=refresh)


@router.get("/{order_id}")
def fetch_order(order_id: str, refresh: bool = False):
    return yc_adapter.fetch_and_cache_order(order_id=order_id, refresh=refresh)
