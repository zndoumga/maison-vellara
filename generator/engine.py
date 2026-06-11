"""
Generation engine — produces one day (or one intra-day window) of raw data
across all three sources, honouring cross-source dependencies, and hands the
results to a sink.

Order matters: POS creates clients and depletes inventory, so it runs before
the CRM delta and the inventory snapshot; ecom events feed ecom orders; etc.

Everything is seeded from (date, source[, window]) so re-running a day is
idempotent and reproducible.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

from generators import (
    after_sales, crm, ecom_events, ecom_orders, ecom_returns,
    inventory, pos, wholesale_orders, wholesale_sellthrough,
)
from utils.rng import rng_for

_SEED_DATE = date(2026, 1, 1)


def run(d: date, state, sink, window: tuple[int, int] | None = None) -> dict:
    salt = "" if window is None else f"{window[0]}-{window[1]}"

    # one-time world setup (idempotent)
    inventory.initialise_positions(state, _SEED_DATE)
    wholesale_orders.ensure_assortment(state)

    def t(label, fn):
        t0 = time.time()
        result = fn()
        print(f"    {label}: {time.time()-t0:.1f}s", flush=True)
        return result

    # --- Source 1: boutiques ------------------------------------------------
    pos_rows = t("gen_pos",    lambda: pos.generate(d, state, rng_for(d, "pos", salt), window))
    t("write_pos",             lambda: sink.write_pos(d, pos_rows))

    client_rows = t("gen_crm", lambda: crm.generate_delta(d, state))
    t("write_crm",             lambda: sink.write_clients(d, client_rows))

    inv_rows = t("gen_inv",    lambda: inventory.generate_snapshot(d, state, rng_for(d, "inventory", salt)))
    t("write_inv",             lambda: sink.write_inventory(d, inv_rows))

    as_rows = t("gen_as",      lambda: after_sales.generate(d, state, rng_for(d, "after_sales", salt)))
    t("write_as",              lambda: sink.write_after_sales(d, as_rows))

    # --- Source 2: online store --------------------------------------------
    events, conversions = t("gen_ecom_ev", lambda: ecom_events.generate(d, state, rng_for(d, "ecom_events", salt), window))
    t("write_ecom_ev",         lambda: sink.write_ecom_events(d, events))

    orders = t("gen_ecom_ord", lambda: ecom_orders.generate(d, state, rng_for(d, "ecom_orders", salt), conversions))
    t("write_ecom_ord",        lambda: sink.write_ecom_orders(d, orders))

    returns = t("gen_ecom_ret",lambda: ecom_returns.generate(d, state, rng_for(d, "ecom_returns", salt)))
    t("write_ecom_ret",        lambda: sink.write_ecom_returns(d, returns))

    # --- Source 3: wholesale -----------------------------------------------
    files = t("gen_whl",       lambda: wholesale_orders.generate(d, state, rng_for(d, "wholesale_orders", salt)))
    for partner_id, kind, filename, content in files:
        sink.write_wholesale_file(partner_id, kind, filename, content)

    sellthrough = t("gen_st",  lambda: wholesale_sellthrough.generate(d, state, rng_for(d, "wholesale_sellthrough", salt)))
    for partner_id, doc in sellthrough:
        sink.write_sellthrough(partner_id, d, doc)

    # housekeeping: keep the returns/corrections lookback window bounded
    state.prune_transactions(d - timedelta(days=70))
    state.prune_ecom_orders(d - timedelta(days=35))
    state.commit()

    return {
        "date": d.isoformat(),
        "pos": len(pos_rows),
        "clients": len(client_rows),
        "inventory": len(inv_rows),
        "after_sales": len(as_rows),
        "ecom_events": len(events),
        "ecom_orders": len(orders),
        "ecom_returns": len(returns),
        "wholesale_files": len(files),
        "sellthrough": len(sellthrough),
    }
