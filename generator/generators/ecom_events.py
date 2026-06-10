"""
Online store clickstream.

Sessions flow through a funnel: session_start -> product_view(s) -> add_to_cart
-> checkout_started -> checkout_completed -> session_end. Most sessions are
anonymous; drop-off at each step follows config.FUNNEL. Sessions that reach
checkout_completed are returned as `conversions` for the orders generator.

Online traffic peaks in the evening (people browsing at home), independent of
boutique opening hours.
"""
from __future__ import annotations

import random
from datetime import date, time

import catalog
import config
from utils import identity
from utils.rng import chance, weighted_choice, weighted_pairs, poisson, jitter
from utils.timeutils import local_to_utc

# Evening-weighted hour-of-day shape (UTC-ish, kept simple/global).
_HOUR_SHAPE = {h: w for h, w in {
    0: 0.4, 1: 0.2, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.2, 6: 0.3, 7: 0.5,
    8: 0.7, 9: 0.8, 10: 0.9, 11: 1.0, 12: 1.0, 13: 0.9, 14: 0.9, 15: 0.9,
    16: 1.0, 17: 1.1, 18: 1.2, 19: 1.4, 20: 1.6, 21: 1.5, 22: 1.1, 23: 0.7,
}.items()}

_BASE_SESSIONS = 850  # average sessions/day before season & day-of-week scaling


def _sample_hour(rng: random.Random, window: tuple[int, int] | None) -> int:
    hours = list(range(24))
    if window is not None:
        hours = [h for h in hours if window[0] <= h < window[1]]
        if not hours:
            hours = [window[0] if window[0] < 24 else 12]
    weights = [_HOUR_SHAPE.get(h, 0.5) for h in hours]
    return rng.choices(hours, weights=weights, k=1)[0]


def _ts(rng: random.Random, d: date, window) -> str:
    h = _sample_hour(rng, window)
    t = time(h, rng.randint(0, 59), rng.randint(0, 59))
    return local_to_utc(d, t, "UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def generate(d: date, state, rng: random.Random, window: tuple[int, int] | None = None):
    month_mult = config.MONTHLY_MULTIPLIERS[d.month - 1]
    # online skews opposite to stores on weekends: a touch higher midweek evenings
    dow = d.weekday()
    dow_mult = 1.15 if dow in (6, 0) else 1.0  # Sun/Mon evenings strong online

    scale = 1.0
    if window is not None:
        scale = max(0.0, (min(window[1], 24) - window[0]) / 24)
    expected = _BASE_SESSIONS * month_mult * dow_mult * scale
    n_sessions = poisson(rng, jitter(rng, expected, 0.15))

    f = config.FUNNEL
    events: list[dict] = []
    conversions: list[dict] = []

    for _ in range(n_sessions):
        s_seq = state.next_seq("session")
        sid = identity.session_id(d, s_seq)
        country = weighted_pairs(rng, config.ECOM_SHIPPING_COUNTRIES)
        device = weighted_choice(rng, config.ECOM_DEVICE_TYPES, config.ECOM_DEVICE_WEIGHTS)
        referrer = weighted_choice(rng, config.ECOM_REFERRERS, config.ECOM_REFERRER_WEIGHTS)

        # ~40% logged in (60% anonymous)
        client_id = None
        if state.ecom_client_count() > 30 and chance(rng, 0.40):
            c = state.sample_ecom_client(rng)
            client_id = c["id"] if c else None

        def emit(event_type, sku_id=None, page="/"):
            e_seq = state.next_seq("event")
            events.append({
                "event_id": identity.event_id(e_seq),
                "session_id": sid,
                "client_id": client_id,
                "event_type": event_type,
                "timestamp": _ts(rng, d, window),
                "sku_id": sku_id,
                "page": page,
                "referrer": referrer,
                "device_type": device,
                "country": country,
            })

        emit("session_start", page="/")

        viewed_skus: list[str] = []
        if chance(rng, f["session_to_product_view"]):
            ids, weights = catalog.category_demand_weights()
            n_views = 1 + poisson(rng, 1.5)
            for _v in range(n_views):
                sku = rng.choices(ids, weights=weights, k=1)[0]
                viewed_skus.append(sku)
                slug = sku.lower()
                emit("product_view", sku_id=sku, page=f"/products/{slug}")

        cart_skus: list[str] = []
        for sku in viewed_skus:
            if chance(rng, f["product_view_to_add_to_cart"]):
                cart_skus.append(sku)
                emit("add_to_cart", sku_id=sku, page="/cart")

        completed = False
        if cart_skus and chance(rng, f["add_to_cart_to_checkout"]):
            emit("checkout_started", page="/checkout")
            if chance(rng, f["checkout_to_complete"]):
                emit("checkout_completed", page="/checkout/confirmation")
                completed = True
                conversions.append({
                    "session_id": sid,
                    "client_id": client_id,
                    "sku_ids": cart_skus,
                    "device_type": device,
                    "country": country,
                    "referrer": referrer,
                    "timestamp": _ts(rng, d, window),
                })

        emit("session_end", page="/")

    return events, conversions
