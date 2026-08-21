"""Wraps manual_split.py's pure helpers unchanged."""

from .. import sys_path  # noqa: F401

from manual_split import _slugify, _parse_service  # noqa: E402

slugify = _slugify
parse_service = _parse_service
