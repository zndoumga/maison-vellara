"""
Wholesale daily sell-through (partner portal API data).

Each partner reports, per day, what its end-customers bought: units sold, stock
remaining, revenue, and the buyer's details. The **only** fields guaranteed
across all three partners are customer name, phone, email and country of
residence — but each partner names and nests them completely differently, and
adds its own extra fields. Reconciling these is a downstream (dbt) problem.

  GLF: { report_date, partner_id, store, items:[ {sku, qty_sold_today, qty_stock,
         revenue_eur, client:{client_nom, client_prenom, client_email,
         client_telephone, client_pays, carte_fidelite}} ] }
  LBM: { date, partner, sales:{ <sku>:{units, stock_remaining, ca_eur,
         buyer:{last_name, first_name, email_address, mobile, country_code,
         loyalty_id}} } }
  PRT: [ {dt, art, vte, stk, ca, cli_nom, cli_prenom, cli_mail, cli_tel, cli_pays} ]

Some days a partner portal is down → no document (the engine emits nothing,
mirroring a 404/empty response).
"""
from __future__ import annotations

import random
from datetime import date

import catalog
import config
from utils import people
from utils.rng import chance, poisson, weighted_pairs

# department-store shoppers: French-heavy but very international (tourists)
_PARTNER_NATIONALITIES = [
    ("FR", 0.40), ("CN", 0.14), ("US", 0.10), ("JP", 0.07), ("GB", 0.06),
    ("AE", 0.05), ("KR", 0.04), ("IT", 0.04), ("DE", 0.03), ("RU", 0.03),
    ("BR", 0.02), ("OTHER", 0.02),
]
_NAT_COUNTRY = {
    "FR": "FR", "CN": "CN", "US": "US", "JP": "JP", "GB": "GB", "AE": "AE",
    "KR": "KR", "IT": "IT", "DE": "DE", "RU": "RU", "BR": "BR", "OTHER": "FR",
}
_GLF_STORE = "Paris Haussmann"


def _loyalty_ref(partner: str, seq: int) -> str:
    if partner == "GLF":
        return f"GLF{seq:06d}"
    if partner == "LBM":
        return f"LBM-{seq:05d}"
    return f"PR{seq:06d}"


def _get_customer(state, rng: random.Random, partner: str) -> dict:
    """Return a normalised customer dict, reusing or creating a partner customer."""
    if state.partner_customer_count(partner) > 20 and chance(rng, 0.55):
        c = state.sample_partner_customer(rng, partner)
        if c:
            return c
    seq = state.partner_customer_count(partner) + 1
    nat = weighted_pairs(rng, _PARTNER_NATIONALITIES)
    person = people.make_person(rng, nat)
    rec = {
        "ref": _loyalty_ref(partner, seq),
        "first_name": person["first_name"],
        "last_name": person["last_name"],
        "email": person["email"],
        "phone": person["phone"],
        "country": _NAT_COUNTRY.get(nat, "FR"),
    }
    state.add_partner_customer(partner, rec["ref"], rec)
    return rec


def _build_sales(state, rng: random.Random, partner: str, d: date) -> list[dict]:
    """Pick what sold today from in-stock assortment; decrement partner stock."""
    in_stock = [s for s in state.partner_assortment(partner) if (state.get_partner_stock(partner, s) or 0) > 0]
    if not in_stock:
        return []
    month_mult = config.MONTHLY_MULTIPLIERS[d.month - 1]
    dow_mult = config.DOW_MULTIPLIERS[d.weekday()]
    total = poisson(rng, 6.0 * month_mult * dow_mult)

    weights = [catalog.sku_index()[s]["demand_weight"] for s in in_stock]
    sales: list[dict] = []
    for _ in range(total):
        sku = rng.choices(in_stock, weights=weights, k=1)[0]
        stock = state.get_partner_stock(partner, sku) or 0
        if stock <= 0:
            continue
        units = 1
        state.set_partner_stock(partner, sku, stock - units)
        revenue = round(catalog.sku_index()[sku]["price_by_currency"]["EUR"] * units, 2)
        sales.append({
            "sku": sku, "units": units,
            "stock_remaining": stock - units, "revenue": revenue,
            "customer": _get_customer(state, rng, partner),
        })
    return sales


def generate(d: date, state, rng: random.Random) -> list[tuple[str, dict]]:
    """Return list of (partner_id, document). Partners that are 'down' are omitted."""
    out: list[tuple[str, dict]] = []
    for partner_cfg in config.WHOLESALE_PARTNERS:
        partner = partner_cfg["partner_id"]
        if chance(rng, 0.10):  # portal outage
            continue
        sales = _build_sales(state, rng, partner, d)
        out.append((partner, _render(partner, d, sales)))
    return out


# ---------------------------------------------------------------------------
# partner-specific document renderers
# ---------------------------------------------------------------------------
def _render(partner: str, d: date, sales: list[dict]) -> dict:
    if partner == "GLF":
        return {
            "report_date": d.isoformat(),
            "partner_id": "GLF",
            "store": _GLF_STORE,
            "items": [{
                "sku": s["sku"],
                "qty_sold_today": s["units"],
                "qty_stock": s["stock_remaining"],
                "revenue_eur": s["revenue"],
                "client": {
                    "client_nom": s["customer"]["last_name"],
                    "client_prenom": s["customer"]["first_name"],
                    "client_email": s["customer"]["email"],
                    "client_telephone": s["customer"]["phone"],
                    "client_pays": s["customer"]["country"],
                    "carte_fidelite": s["customer"]["ref"],
                },
            } for s in sales],
        }

    if partner == "LBM":
        # keyed by sku; if a sku appears twice, the later buyer wins (their system overwrites)
        sales_map = {}
        for s in sales:
            sales_map[s["sku"]] = {
                "units": s["units"],
                "stock_remaining": s["stock_remaining"],
                "ca_eur": s["revenue"],
                "buyer": {
                    "last_name": s["customer"]["last_name"],
                    "first_name": s["customer"]["first_name"],
                    "email_address": s["customer"]["email"],
                    "mobile": s["customer"]["phone"],
                    "country_code": s["customer"]["country"],
                    "loyalty_id": s["customer"]["ref"],
                },
            }
        return {"date": d.isoformat(), "partner": "LBM", "sales": sales_map}

    # PRT — bare flat array, short keys (their portal returns a JSON list, not an object)
    return [{
        "dt": d.strftime("%Y%m%d"),
        "art": s["sku"],
        "vte": s["units"],
        "stk": s["stock_remaining"],
        "ca": s["revenue"],
        "cli_nom": s["customer"]["last_name"],
        "cli_prenom": s["customer"]["first_name"],
        "cli_mail": s["customer"]["email"],
        "cli_tel": s["customer"]["phone"],
        "cli_pays": s["customer"]["country"],
    } for s in sales]
