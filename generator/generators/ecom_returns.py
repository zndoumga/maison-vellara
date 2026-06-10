"""
Online returns — raised 7-30 days after the original order, referencing it.
Returns are their own JSON documents (a separate API resource), partially
mirroring the original line items with a reason code.
"""
from __future__ import annotations

import random
from datetime import date, time

import config
from utils import identity
from utils.rng import chance, poisson
from utils.timeutils import local_to_utc

_REASON_CODES = ["size_fit", "not_as_expected", "changed_mind", "damaged_in_transit",
                 "wrong_item", "quality_concern"]


def generate(d: date, state, rng: random.Random) -> list[dict]:
    # roughly 8% of orders eventually come back; spread over the return window
    n = poisson(rng, 3.0)
    returns: list[dict] = []
    for _ in range(n):
        orig = state.sample_recent_ecom_order(rng, min_age_days=7, max_age_days=30, on_date=d)
        if not orig:
            continue
        seq = state.next_seq("ecom_return")
        rid = identity.ecom_return_id(d, seq)

        # return a subset of the order's lines
        returned_lines = [li for li in orig["line_items"] if chance(rng, 0.7)] or orig["line_items"][:1]
        refund = round(sum(li["unit_price"] * li["quantity"] for li in returned_lines), 2)
        t = time(rng.randint(8, 22), rng.randint(0, 59), rng.randint(0, 59))

        returns.append({
            "return_id": rid,
            "order_id": orig["order_id"],
            "created_at": local_to_utc(d, t, "UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
            "client": orig["client"],
            "reason_code": rng.choice(_REASON_CODES),
            "status": rng.choice(["requested", "approved", "received", "refunded"]),
            "currency": orig["currency"],
            "refund_amount": refund,
            "line_items": [
                {"sku_id": li["sku_id"], "quantity": li["quantity"], "unit_price": li["unit_price"]}
                for li in returned_lines
            ],
        })
        state.mark_ecom_returned(orig["order_id"])
    return returns
