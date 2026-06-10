"""
Inventory.

A mutable position per (store, SKU) is the working truth; each day we emit an
append-only snapshot (what Fabric reads). Sales decrement on-hand, returns
restock it, and when a SKU runs low a replenishment is scheduled that lands
3-7 days later. On-hand is allowed to dip negative for short windows — a real,
common timing artdefact between the till and the stock system.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

import catalog
import config
from utils.rng import jitter as _jitter

# Nominal target stock per category (luxury scarcity: handbags & jackets are
# deliberately thin; small leather goods turn over fast and sit deeper).
_NOMINAL = {
    "Handbags": 5,
    "Small Leather Goods": 25,
    "Shoes": 12,
    "Leather Jackets": 6,
    "Travel Bags": 8,
    "Belts": 20,
}
_TIER_MULT = {"flagship": 1.5, "standard": 1.0}

_STORE = {s["store_id"]: s for s in config.STORES}


def _nominal_for(store_id: str, sku_id: str) -> int:
    cat = catalog.sku_index()[sku_id]["category"]
    tier = _STORE[store_id]["tier"]
    return max(1, round(_NOMINAL[cat] * _TIER_MULT[tier]))


def initialise_positions(state, seed_date: date) -> None:
    """Seed opening stock for every (store, SKU). Idempotent."""
    if state.positions_initialised():
        return
    rng = random.Random(20260101)
    for store in config.STORES:
        for sku in catalog.all_sku_ids():
            nominal = _nominal_for(store["store_id"], sku)
            on_hand = max(0, round(_jitter(rng, nominal, 0.4)))
            state.upsert_position(
                {
                    "store_id": store["store_id"], "sku_id": sku,
                    "qty_on_hand": on_hand, "qty_reserved": 0, "qty_in_transit": 0,
                    "last_replenishment_dt": seed_date.isoformat(),
                    "reorder_flag": 0, "replenish_eta": None,
                }
            )


def apply_sale(state, store_id: str, sku_id: str, qty: int) -> None:
    pos = state.get_position(store_id, sku_id)
    if not pos:
        return
    pos["qty_on_hand"] -= qty
    state.upsert_position(pos)


def restock(state, store_id: str, sku_id: str, qty: int) -> None:
    pos = state.get_position(store_id, sku_id)
    if not pos:
        return
    pos["qty_on_hand"] += qty
    state.upsert_position(pos)


def generate_snapshot(d: date, state, rng: random.Random) -> list[dict]:
    """Advance replenishment, raise reorders, and emit the day's snapshot rows."""
    rows = []
    snapshot_ts = f"{d.isoformat()}T20:00:00Z"
    for pos in state.all_positions():
        store_id, sku_id = pos["store_id"], pos["sku_id"]

        # 1) receive any replenishment that has arrived
        eta = pos.get("replenish_eta")
        if eta and eta <= d.isoformat():
            pos["qty_on_hand"] += pos["qty_in_transit"]
            pos["qty_in_transit"] = 0
            pos["reorder_flag"] = 0
            pos["replenish_eta"] = None
            pos["last_replenishment_dt"] = d.isoformat()

        # 2) raise a reorder if low and nothing already inbound
        nominal = _nominal_for(store_id, sku_id)
        threshold = max(1, round(0.3 * nominal))
        if pos["qty_on_hand"] <= threshold and pos["qty_in_transit"] == 0:
            reorder_qty = max(nominal - max(pos["qty_on_hand"], 0), nominal)
            pos["qty_in_transit"] = reorder_qty
            pos["reorder_flag"] = 1
            lead = rng.randint(3, 7)
            pos["replenish_eta"] = (d + timedelta(days=lead)).isoformat()

        state.upsert_position(pos)

        rows.append(
            {
                "snapshot_ts": snapshot_ts,
                "store_id": store_id,
                "sku_id": sku_id,
                "qty_on_hand": pos["qty_on_hand"],
                "qty_reserved": pos["qty_reserved"],
                "qty_in_transit": pos["qty_in_transit"],
                "last_replenishment_dt": pos.get("last_replenishment_dt"),
                "reorder_flag": bool(pos["reorder_flag"]),
            }
        )
    return rows
