from fastapi import APIRouter, Depends, Query

from ..dependencies import require_yc_linked
from ..services import yc_adapter
from ..services.user_store import AuthedUser

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
def list_orders(
    page: int = Query(1, ge=1),
    count: int = Query(20, ge=1, le=50),
    user: AuthedUser = Depends(require_yc_linked),
):
    raw = yc_adapter.list_orders(user, page=page, count=count)
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
def fetch_latest(refresh: bool = False, user: AuthedUser = Depends(require_yc_linked)):
    return yc_adapter.fetch_and_cache_order(user, order_id="", refresh=refresh)


@router.get("/{order_id}")
def fetch_order(order_id: str, refresh: bool = False, user: AuthedUser = Depends(require_yc_linked)):
    return yc_adapter.fetch_and_cache_order(user, order_id=order_id, refresh=refresh)
