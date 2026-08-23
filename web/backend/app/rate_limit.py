"""Shared slowapi Limiter instance — its own module so both main.py (which
registers it on the app) and routers (which decorate endpoints with it) can
import it without a circular dependency."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
