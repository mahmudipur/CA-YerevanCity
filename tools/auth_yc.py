#!/usr/bin/env python3
"""
Authenticate with Yerevan City API via phone OTP.

Flow:
  1. GET /Sms/ConfirmCode  → server returns a confirmCode token
  2. POST /Sms/SendCode    → SMS OTP sent to your phone
  3. POST /Sms/Verify      → submit OTP → receive JWT

The JWT is written back to YC_JWT in .env.
If YC_DEVICE_ID is empty a stable UUID is generated and saved once.

Usage:
  python tools/auth_yc.py
"""

import os
import sys
import uuid
from pathlib import Path

# Make sibling tools importable
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv, set_key
from yc_client import YCError, confirm_code, send_code, verify

ENV_PATH = Path(__file__).parent.parent / ".env"


def main() -> None:
    load_dotenv(ENV_PATH)

    phone_local = os.getenv("YC_PHONE_LOCAL", "").strip()
    phone_e164  = os.getenv("YC_PHONE_E164",  "").strip()

    if not phone_local or not phone_e164:
        print("Error: YC_PHONE_LOCAL and YC_PHONE_E164 must be set in .env")
        sys.exit(1)

    # Generate device ID once and persist it
    device_id = os.getenv("YC_DEVICE_ID", "").strip()
    if not device_id:
        device_id = uuid.uuid4().hex + "tAyn"   # matches format seen in Postman
        set_key(str(ENV_PATH), "YC_DEVICE_ID", device_id)
        print(f"Generated device ID: {device_id}")

    print(f"Requesting OTP for {phone_e164} ...")

    try:
        code = confirm_code()
        send_code(phone_local, device_id, code)
    except YCError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"SMS sent. Check your phone.")
    otp = input("Enter 6-digit OTP: ").strip()

    if len(otp) != 6 or not otp.isdigit():
        print("Invalid OTP format. Expected exactly 6 digits.")
        sys.exit(1)

    try:
        jwt = verify(phone_e164, otp)
    except YCError as e:
        print(f"Verification failed: {e}")
        sys.exit(1)

    set_key(str(ENV_PATH), "YC_JWT", jwt)
    print("Authenticated. JWT saved to .env")
    print(f"\nNext: python tools/fetch_order.py")


if __name__ == "__main__":
    main()
