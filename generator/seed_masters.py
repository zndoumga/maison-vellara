"""
Master / reference data — the operational source masters (store list, advisor
roster, technician roster, product catalogue, wholesale partners).

These are realistic *source* masters, not modelled dimensions: dbt still has to
clean and conform them. Written once (idempotent overwrite).
"""
from __future__ import annotations

import catalog
import config


def build_masters() -> dict[str, list[dict]]:
    products = [
        {
            "sku_id": s["sku_id"], "category": s["category"], "style": s["style"],
            "color": s["color"], "product_name": s["product_name"],
            "base_price_eur": s["base_price_eur"],
        }
        for s in catalog.build_catalog()
    ]
    stores = [
        {k: store[k] for k in ("store_id", "name", "city", "country", "timezone", "tier")}
        for store in config.STORES
    ]
    return {
        "stores": stores,
        "advisors": [dict(a) for a in config.ADVISORS],
        "technicians": [dict(t) for t in config.TECHNICIANS],
        "products": products,
        "wholesale_partners": [dict(p) for p in config.WHOLESALE_PARTNERS],
    }
