"""
Online store orders — nested JSON documents (Shopify-shaped).

Built from the checkout conversions emitted by the events generator. Each order
embeds its line items, customer and shipping address in one document (no joins),
which is exactly what lands from a modern e-commerce API.

Online customers partially overlap boutique CRM clients by email/phone (some
shoppers are known clients), but the generator never links them — resolving
that identity is a downstream (dbt) problem.
"""
from __future__ import annotations

import random
from datetime import date

import catalog
import config
from generators.crm import choose_nationality, _NATIONALITY_COUNTRY
from utils import identity, people
from utils.rng import chance

_CHANNEL_BY_REFERRER = {
    "direct": "direct", "google": "paid_search", "instagram": "social",
    "email_campaign": "email", "other": "referral",
}
_DISCOUNT_CODES = ["WELCOME10", "PRIVATE15", "VIP20", "SPRING10", "NEWSLETTER10"]


def _resolve_client(state, rng: random.Random, conv: dict, country: str) -> dict:
    # logged-in shopper → reuse existing online client
    if conv["client_id"]:
        c = state.sample_ecom_client(rng)
        if c:
            return c

    seq = state.next_seq("ecom_client")
    cid = identity.ecom_client_id(seq)

    # ~30% of new online clients mirror an existing boutique client (same
    # person shopping online) — the seam dbt has to stitch back together.
    crm_client = state.sample_existing_client(rng) if chance(rng, 0.30) else None
    if crm_client:
        rec = {
            "id": cid,
            "email": crm_client.get("email") or f"{cid.lower()}@guest.vellara.com",
            "first_name": crm_client["first_name"],
            "last_name": crm_client["last_name"],
            "phone": crm_client.get("phone"),
            "country": country,
        }
    else:
        nat = choose_nationality(rng)
        person = people.make_person(rng, nat)
        rec = {
            "id": cid,
            "email": person["email"],
            "first_name": person["first_name"],
            "last_name": person["last_name"],
            "phone": person["phone"] if not chance(rng, 0.4) else None,
            "country": country,
        }
    state.add_ecom_client(rec)
    return rec


def _address(rng: random.Random, country: str) -> dict:
    locale = config.NATIONALITY_LOCALE.get(country, "en_US")
    fake = people._faker_for(locale)
    fake.seed_instance(rng.random())
    try:
        city = fake.city()
        zip_code = fake.postcode()
    except Exception:
        city, zip_code = "Paris", "75001"
    return {"country": country, "city": str(city), "zip": str(zip_code)}


def generate(d: date, state, rng: random.Random, conversions: list[dict]) -> list[dict]:
    orders: list[dict] = []
    for conv in conversions:
        seq = state.next_seq("ecom_order")
        oid = identity.order_id(d, seq)
        country = conv["country"]
        client = _resolve_client(state, rng, conv, country)

        line_items = []
        subtotal = 0.0
        for i, sku in enumerate(conv["sku_ids"], start=1):
            s = catalog.sku_index()[sku]
            qty = 1 if not chance(rng, 0.05) else 2
            price = s["price_by_currency"]["EUR"]
            subtotal += price * qty
            line_items.append({
                "line_id": i,
                "sku_id": sku,
                "product_name": s["product_name"],
                "quantity": qty,
                "unit_price": price,
                "discount": 0.0,
            })

        discount_code = None
        discount_amount = 0.0
        if chance(rng, 0.12):
            discount_code = rng.choice(_DISCOUNT_CODES)
            pct = int(discount_code[-2:]) if discount_code[-2:].isdigit() else 10
            discount_amount = round(subtotal * pct / 100.0, 2)

        shipping_cost = 0.0 if subtotal >= 300 else 25.0
        total = round(subtotal - discount_amount + shipping_cost, 2)

        failed = chance(rng, 0.05)
        order = {
            "order_id": oid,
            "created_at": conv["timestamp"],
            "status": "payment_failed" if failed else "confirmed",
            "financial_status": "failed" if failed else "paid",
            "client": {
                "id": client["id"],
                "email": client.get("email"),
                "first_name": client.get("first_name"),
                "last_name": client.get("last_name"),
            },
            "shipping_address": _address(rng, country),
            "currency": "EUR",
            "subtotal": round(subtotal, 2),
            "shipping_cost": shipping_cost,
            "discount_code": discount_code,
            "discount_amount": discount_amount,
            "total": total,
            "line_items": line_items,
            "channel": _CHANNEL_BY_REFERRER.get(conv["referrer"], "direct"),
            "device_type": conv["device_type"],
            "session_id": conv["session_id"],
        }
        orders.append(order)

        if not failed:
            state.add_ecom_order_ref({
                "order_id": oid,
                "order_date": d.isoformat(),
                "client": order["client"],
                "currency": "EUR",
                "total": total,
                "line_items": line_items,
            })
    return orders
