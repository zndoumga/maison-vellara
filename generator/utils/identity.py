"""
ID factories. All IDs are human-readable and encode enough context to be
traceable back to a store / date, the way real operational systems format them.

Sequence numbers come from the StateStore so they survive across runs.
"""
from __future__ import annotations

from datetime import date


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def transaction_id(store_id: str, d: date, seq: int) -> str:
    return f"RCPT-{store_id}-{_ymd(d)}-{seq:04d}"


def correction_id(store_id: str, d: date, seq: int) -> str:
    return f"CORR-{store_id}-{_ymd(d)}-{seq:04d}"


def return_id(store_id: str, d: date, seq: int) -> str:
    return f"RET-{store_id}-{_ymd(d)}-{seq:04d}"


def client_id(seq: int) -> str:
    return f"CLI-{seq:06d}"


def ecom_client_id(seq: int) -> str:
    return f"WCLI-{seq:06d}"


def order_id(d: date, seq: int) -> str:
    return f"WEB-{_ymd(d)}-{seq:04d}"


def session_id(d: date, seq: int) -> str:
    return f"SES-{_ymd(d)}-{seq:05d}"


def event_id(seq: int) -> str:
    return f"EVT-{seq:08d}"


def repair_id(d: date, seq: int) -> str:
    return f"AS-{_ymd(d)}-{seq:04d}"


def ecom_return_id(d: date, seq: int) -> str:
    return f"WRET-{_ymd(d)}-{seq:04d}"
