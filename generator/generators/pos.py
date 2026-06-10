"""
POS transactions — one row per line item, the way a till export looks (the
transaction header repeats on every line).

Produces three transaction types:
  SALE        normal purchase, 1..n line items
  RETURN      credit against a prior sale (negative quantities), advisor NULL
  CORRECTION  French facture rectificative — the original invoice is never
              deleted; a correcting invoice is issued referencing it, advisor NULL

Side effects on state: creates/returns clients, decrements (and on returns,
restocks) inventory positions, and records transaction refs so future days can
raise returns/corrections against them.
"""
from __future__ import annotations

import random
from datetime import date

import catalog
import config
from generators import crm, inventory
from utils import identity
from utils.rng import chance, weighted_choice, poisson, jitter
from utils.timeutils import sample_local_time, local_to_utc

# store_id -> [advisor_id, ...]
_ADVISORS_BY_STORE: dict[str, list[str]] = {}
for _a in config.ADVISORS:
    _ADVISORS_BY_STORE.setdefault(_a["store_id"], []).append(_a["advisor_id"])

_STORE = {s["store_id"]: s for s in config.STORES}

_LINE_COUNT_CHOICES = [1, 2, 3, 4]
_LINE_COUNT_WEIGHTS = [0.70, 0.22, 0.06, 0.02]


def _pick_skus(rng: random.Random, n: int) -> list[str]:
    ids, weights = catalog.category_demand_weights()
    return rng.choices(ids, weights=weights, k=n)


def _row(**kw) -> dict:
    """Full POS row with every column present (NULLs where not applicable)."""
    base = {
        "transaction_id": None, "store_id": None, "terminal_id": None,
        "transaction_date": None, "transaction_time": None, "advisor_id": None,
        "client_id": None, "line_number": None, "sku_id": None, "quantity": None,
        "unit_price": None, "discount_amount": 0.0, "currency": None,
        "payment_method": None, "transaction_type": None,
        "original_transaction_id": None, "reason_code": None, "corrected_amount": None,
    }
    base.update(kw)
    return base


def _volume_scale_for_window(store, window):
    """Fraction of the store's open hours covered by an intra-day window."""
    if window is None:
        return 1.0
    open_h, close_h = config.STORE_HOURS[store["store_id"]]
    lo, hi = max(open_h, window[0]), min(close_h, window[1])
    total = max(close_h - open_h, 1)
    return max(0.0, (hi - lo) / total)


def generate(d: date, state, rng: random.Random, window: tuple[int, int] | None = None) -> list[dict]:
    rows: list[dict] = []
    month_mult = config.MONTHLY_MULTIPLIERS[d.month - 1]
    dow_mult = config.DOW_MULTIPLIERS[d.weekday()]

    for store in config.STORES:
        store_id = store["store_id"]
        currency = config.STORE_CURRENCY[store_id]
        open_h, close_h = config.STORE_HOURS[store_id]
        tz = store["timezone"]
        advisors = _ADVISORS_BY_STORE[store_id]
        scale = _volume_scale_for_window(store, window)
        if scale <= 0:
            continue

        expected = store["avg_daily_tx"] * dow_mult * month_mult * scale
        n_tx = poisson(rng, jitter(rng, expected, 0.15))

        day_sale_ids: list[str] = []

        for _ in range(n_tx):
            seq = state.next_seq("receipt", reset_scope=f"{store_id}:{d.isoformat()}")
            tx_id = identity.transaction_id(store_id, d, seq)
            terminal = f"TRM-{rng.randint(1, 3):02d}"
            advisor = rng.choice(advisors)
            t = sample_local_time(rng, open_h, close_h, window)
            t_str = t.strftime("%H:%M:%S")
            when_iso = local_to_utc(d, t, tz).strftime("%Y-%m-%dT%H:%M:%SZ")
            payment = weighted_choice(rng, config.PAYMENT_METHODS, config.PAYMENT_METHOD_WEIGHTS)

            # client: 5-8% anonymous, else returning or newly registered
            client_id = None
            if not chance(rng, rng.uniform(0.05, 0.08)):
                existing = None
                if state.client_count() > 50 and chance(rng, 0.72):
                    # half the time the client is loyal to this boutique, half
                    # the time they're shopping the network (travelling clientele)
                    scope = store_id if chance(rng, 0.5) else None
                    existing = state.sample_existing_client(rng, scope)
                if existing:
                    client_id = existing["client_id"]
                    state.touch_client(client_id, when_iso)
                else:
                    new_c = crm.make_new_client(state, rng, d, store_id, advisor, when_iso)
                    client_id = new_c["client_id"]

            n_lines = weighted_choice(rng, _LINE_COUNT_CHOICES, _LINE_COUNT_WEIGHTS)
            skus = _pick_skus(rng, n_lines)
            has_discount = chance(rng, 0.03)
            line_items = []
            total = 0.0
            for i, sku in enumerate(skus, start=1):
                qty = 1 if not chance(rng, 0.06) else 2
                price = catalog.price_for(sku, currency)
                discount = round(price * qty * rng.uniform(0.05, 0.10), 2) if has_discount else 0.0
                total += price * qty - discount
                line_items.append(
                    {"sku_id": sku, "quantity": qty, "unit_price": price, "discount_amount": discount}
                )
                rows.append(
                    _row(
                        transaction_id=tx_id, store_id=store_id, terminal_id=terminal,
                        transaction_date=d.isoformat(), transaction_time=t_str,
                        advisor_id=advisor, client_id=client_id, line_number=i,
                        sku_id=sku, quantity=qty, unit_price=price, discount_amount=discount,
                        currency=currency, payment_method=payment, transaction_type="SALE",
                    )
                )
                inventory.apply_sale(state, store_id, sku, qty)

            state.add_transaction_ref(
                {
                    "transaction_id": tx_id, "store_id": store_id, "txn_date": d.isoformat(),
                    "client_id": client_id, "currency": currency, "total": round(total, 2),
                    "advisor_id": advisor, "terminal_id": terminal, "payment_method": payment,
                    "line_items": line_items,
                }
            )
            day_sale_ids.append(tx_id)

        # --- RETURNS: ~4% of today's volume, against prior sales -----------
        n_returns = poisson(rng, n_tx * 0.04)
        for _ in range(n_returns):
            orig = state.sample_recent_sale(rng, store_id, min_age_days=1, max_age_days=60, on_date=d)
            if not orig:
                continue
            seq = state.next_seq("receipt", reset_scope=f"{store_id}:{d.isoformat()}")
            ret_id = identity.transaction_id(store_id, d, seq)
            t = sample_local_time(rng, open_h, close_h, window)
            t_str = t.strftime("%H:%M:%S")
            for i, li in enumerate(orig["line_items"], start=1):
                rows.append(
                    _row(
                        transaction_id=ret_id, store_id=store_id,
                        terminal_id=orig.get("terminal_id"),
                        transaction_date=d.isoformat(), transaction_time=t_str,
                        advisor_id=None, client_id=orig.get("client_id"), line_number=i,
                        sku_id=li["sku_id"], quantity=-li["quantity"], unit_price=li["unit_price"],
                        discount_amount=(-li["discount_amount"] or 0.0), currency=orig["currency"],
                        payment_method=orig.get("payment_method"), transaction_type="RETURN",
                        original_transaction_id=orig["transaction_id"],
                    )
                )
                inventory.restock(state, store_id, li["sku_id"], li["quantity"])
            state.mark_returned(orig["transaction_id"])

        # --- CORRECTIONS: 1-3% of today's sales (facture rectificative) ----
        corr_rate = rng.uniform(0.01, 0.03)
        for tx_id in day_sale_ids:
            if not chance(rng, corr_rate):
                continue
            ref = next((r for r in rows if r["transaction_id"] == tx_id and r["line_number"] == 1), None)
            if ref is None:
                continue
            seq = state.next_seq("receipt", reset_scope=f"{store_id}:{d.isoformat()}")
            corr_id = identity.correction_id(store_id, d, seq)
            reason = rng.choice(config.CORRECTION_REASON_CODES)
            orig_lines = [r for r in rows if r["transaction_id"] == tx_id and r["transaction_type"] == "SALE"]
            t = sample_local_time(rng, open_h, close_h, window)
            t_str = t.strftime("%H:%M:%S")
            for i, ol in enumerate(orig_lines, start=1):
                adj = round(ol["unit_price"] * rng.uniform(-0.05, 0.05), 2)
                corrected = round(ol["unit_price"] * ol["quantity"] - ol["discount_amount"] + adj, 2)
                rows.append(
                    _row(
                        transaction_id=corr_id, store_id=store_id, terminal_id=ref["terminal_id"],
                        transaction_date=d.isoformat(), transaction_time=t_str,
                        advisor_id=None, client_id=ref["client_id"], line_number=i,
                        sku_id=ol["sku_id"], quantity=ol["quantity"], unit_price=ol["unit_price"],
                        discount_amount=ol["discount_amount"], currency=ref["currency"],
                        payment_method=ref["payment_method"], transaction_type="CORRECTION",
                        original_transaction_id=tx_id, reason_code=reason, corrected_amount=corrected,
                    )
                )

    return rows
