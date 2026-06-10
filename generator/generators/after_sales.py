"""
After-sales service orders (repairs, cleaning, engraving, authentication,
resizing).

An item can be bought in one country and serviced in another, so an order has a
drop-off `store_id` and an internal `technician_id` but **no advisor**. Orders
progress across days: received -> assessed -> in_progress -> ready -> collected.

The daily export contains every order created or updated that day (its current
state) — the shape of a real service-desk extract.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import catalog
import config
from utils import identity
from utils.rng import chance, weighted_choice

_STATUS_FLOW = ["received", "assessed", "in_progress", "ready", "collected"]

_DESCRIPTIONS = {
    "repair": ["Strap stitching coming apart", "Zip pull replacement", "Corner scuff restoration",
               "Hardware clasp loose", "Lining tear repair", "Heel tip replacement"],
    "cleaning": ["Full leather clean & condition", "Water stain treatment", "Ink mark removal"],
    "engraving": ["Initials embossing", "Hot-stamp monogram", "Re-engrave hardware plate"],
    "authentication": ["Authentication & certificate request", "Pre-resale verification"],
    "resizing": ["Belt resizing", "Strap shortening", "Shoe stretch fitting"],
}

# which technicians can take which service type
_TECH_BY_SERVICE = {
    "repair": ["TECH001", "TECH002", "TECH003", "TECH006"],
    "cleaning": ["TECH005"],
    "engraving": ["TECH004"],
    "authentication": ["TECH001", "TECH002", "TECH006"],
    "resizing": ["TECH001", "TECH002", "TECH006"],
}


def _new_order(state, rng: random.Random, d: date) -> dict:
    seq = state.next_seq("repair")
    store = rng.choice(config.STORES)["store_id"]
    service = weighted_choice(rng, config.AFTER_SALES_SERVICE_TYPES, config.AFTER_SALES_SERVICE_WEIGHTS)
    sku = rng.choice(catalog.all_sku_ids())
    lo, hi = config.AFTER_SALES_SERVICE_DURATION_DAYS[service]
    duration = rng.randint(lo, hi)
    cost_lo, cost_hi = config.AFTER_SALES_SERVICE_COST[service]

    client_id = None
    if not chance(rng, 0.20):  # ~20% have no client record
        existing = state.sample_existing_client(rng)
        client_id = existing["client_id"] if existing else None

    rec = {
        "repair_id": identity.repair_id(d, seq),
        "received_date": d.isoformat(),
        "client_id": client_id,
        "store_id": store,
        "sku_id": sku,
        "service_type": service,
        "description": rng.choice(_DESCRIPTIONS[service]),
        "status": "received",
        "estimated_return_dt": (d + timedelta(days=duration)).isoformat(),
        "actual_return_dt": None,
        "cost": round(rng.uniform(cost_lo, cost_hi), 2),
        "technician_id": rng.choice(_TECH_BY_SERVICE[service]),
        "updated_date": d.isoformat(),
    }
    state.add_open_order(rec)
    return rec


def _advance(rec: dict, rng: random.Random, d: date) -> bool:
    """Maybe move an order one step forward. Returns True if it changed today."""
    if rec["status"] == "collected":
        return False
    idx = _STATUS_FLOW.index(rec["status"])
    # readier orders are more likely to progress; collection waits on the client
    advance_p = 0.45 if rec["status"] != "ready" else 0.30
    if not chance(rng, advance_p):
        return False
    rec["status"] = _STATUS_FLOW[idx + 1]
    rec["updated_date"] = d.isoformat()
    if rec["status"] == "collected":
        # actual return can run a little past the estimate
        slip = rng.randint(-2, 5)
        est = date.fromisoformat(rec["estimated_return_dt"])
        actual = max(d, est + timedelta(days=slip))
        rec["actual_return_dt"] = min(actual, d).isoformat() if actual <= d else d.isoformat()
    return True


def generate(d: date, state, rng: random.Random) -> list[dict]:
    touched: list[dict] = []

    # 1) advance existing open orders
    for rec in state.open_orders():
        if _advance(rec, rng, d):
            state.update_open_order(rec)
            touched.append(rec)

    # 2) create new orders (2-5/day across the network)
    for _ in range(rng.randint(2, 5)):
        touched.append(_new_order(state, rng, d))

    # emit current state of every order touched today
    cols = ["repair_id", "received_date", "client_id", "store_id", "sku_id",
            "service_type", "description", "status", "estimated_return_dt",
            "actual_return_dt", "cost", "technician_id", "updated_date"]
    return [{k: rec.get(k) for k in cols} for rec in touched]
