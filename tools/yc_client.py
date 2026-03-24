"""
Yerevan City API client — synchronous, no DB, no encryption.
Adapted from TMA-YC/backend/app/yc_client/ with async and infrastructure deps stripped.

Base URL : https://apishopv2.yerevan-city.am/api
Auth     : Bearer JWT obtained via 3-step OTP flow (ConfirmCode → SendCode → Verify)
Response : IResponse<T> { success, data, messages[], alertIcon }

Known quirks (discovered in TMA-YC):
  - osType must be 2, not 3 (Postman collection has wrong value)
  - createdOn in GetOfflineOrderById must be YYYY-MM-DD; full ISO datetime causes 500
  - Prices arrive as floats (e.g. 680.19 AMD) — callers should cast to int
  - Order list field is "list", not "items"
  - Order detail items field is "orderItems", not "items"
  - offlineOrderId ("KM...") is the identifier for GetOfflineOrderById
"""

import requests
from typing import Optional

YC_BASE = "https://apishopv2.yerevan-city.am/api"
_TIMEOUT = 30


class YCError(Exception):
    """Raised when the API returns success=false or an HTTP error."""
    pass


def _post(path: str, body: dict, token: Optional[str] = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.post(f"{YC_BASE}{path}", json=body, headers=headers, timeout=_TIMEOUT)
    except requests.exceptions.ConnectionError:
        raise YCError("Cannot reach Yerevan City API. Check your internet connection.")
    except requests.exceptions.Timeout:
        raise YCError(f"Request to {path} timed out after {_TIMEOUT}s.")

    if resp.status_code == 401:
        raise YCError("Unauthorized (401). JWT expired — run: python tools/auth_yc.py")
    if resp.status_code >= 500:
        raise YCError(f"Server error {resp.status_code} on {path}.")
    resp.raise_for_status()

    data = resp.json()
    if not data.get("success", False):
        raw_msgs = data.get("messages", [])
        msgs = []
        for m in raw_msgs:
            if isinstance(m, dict):
                v = m.get("value")
                if v:
                    msgs.append(v)
            else:
                msgs.append(str(m))
        raise YCError("; ".join(msgs) or "Unknown API error")

    return data


# ── Auth ─────────────────────────────────────────────────────────────────────

def confirm_code() -> str:
    """Step 1: Obtain a confirmCode from the server (required before SendCode)."""
    data = _post("/Sms/ConfirmCode", {})
    return str(data["data"])


def send_code(phone_local: str, device_id: str, confirm_code: str) -> None:
    """Step 2: Trigger SMS OTP to phone_local (local format, e.g. '55285320')."""
    _post("/Sms/SendCode", {
        "phoneNumber": phone_local,
        "country": "AM",
        "deviceId": device_id,
        "osType": 2,                 # must be 2 — 3 (from Postman) does not work
        "confirmCode": confirm_code,
    })


def verify(phone_e164: str, code: str) -> str:
    """Step 3: Submit OTP. Returns JWT access token string."""
    data = _post("/Sms/Verify", {"phoneNumber": phone_e164, "code": code})
    return data["data"]["accessToken"]


# ── Orders ───────────────────────────────────────────────────────────────────

def get_orders(token: str, page: int = 1, count: int = 10) -> list[dict]:
    """
    Fetch a page of orders. Returns raw list items from the API.
    Each item has: offlineOrderId, createDate, totalPrice, totalToPay,
                   userDeliveryFee, serviceFee, driverTipAmount, isDelivery,
                   status, paymentMethod, branchAddress, orderOriginType, ...
    """
    data = _post("/Order/UserAllOrdersPaged", {
        "page": page,
        "count": count,
        "orderStatus": None,
        "orderOriginType": None,
        "dateFrom": None,
        "dateTo": None,
    }, token=token)
    # API returns array under "list", not "items"
    return data.get("data", {}).get("list", [])


def get_order_detail(token: str, order_id: str, created_on: str) -> dict:
    """
    Fetch full order detail including line items.
    order_id  : "KM..." string (offlineOrderId from the list)
    created_on: YYYY-MM-DD date string only — full ISO datetime causes a 500
    Returns raw data dict with "orderItems" array.
    """
    data = _post("/Order/GetOfflineOrderById", {
        "orderId": order_id,
        "createdOn": created_on,
    }, token=token)
    return data.get("data", {})
