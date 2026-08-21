"""Wraps split_basket.compute_revolut_currency unchanged."""

from .. import sys_path  # noqa: F401

from split_basket import compute_revolut_currency  # noqa: E402


def cash() -> dict:
    return {"method": "cash"}


def revolut(rate: float, eur_paid: float, is_weekend: bool, is_fair_usage: bool,
            totals: dict, participants: list) -> dict:
    return compute_revolut_currency(rate, eur_paid, is_weekend, is_fair_usage, totals, participants)
