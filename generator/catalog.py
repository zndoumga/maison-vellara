"""
Builds the product catalogue from config.CATEGORIES.

A SKU is a (category, style, color) triple. Price is set per-style in EUR
(deterministic, with a stable per-style variance) and converted to each store's
local currency, rounded to luxury-friendly round numbers.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache

import config

# Short category codes used as SKU prefixes.
CATEGORY_CODE = {
    "Handbags": "HB",
    "Small Leather Goods": "SLG",
    "Shoes": "SH",
    "Leather Jackets": "LJ",
    "Travel Bags": "TB",
    "Belts": "BL",
}


def _slug(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _stable_unit(*parts: str) -> float:
    """Deterministic float in [0,1) from the given strings."""
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _round_price(amount: float, currency: str) -> float:
    if currency == "JPY":
        return float(round(amount / 1000.0) * 1000)
    return float(round(amount / 10.0) * 10)


def _style_price_eur(category: str, style: str) -> float:
    cfg = config.CATEGORIES[category]
    base = cfg["base_price_eur"]
    variance = cfg["price_variance"]
    # Map stable unit [0,1) → [-variance, +variance]
    offset = (_stable_unit(category, style) * 2 - 1) * variance
    return round(base + offset, 2)


@lru_cache(maxsize=1)
def build_catalog() -> list[dict]:
    """Return the full list of SKU dicts."""
    skus: list[dict] = []
    for category, cfg in config.CATEGORIES.items():
        code = CATEGORY_CODE[category]
        for style in cfg["styles"]:
            price_eur = _style_price_eur(category, style)
            for color in cfg["colors"]:
                sku_id = f"{code}-{_slug(style)}-{_slug(color)}"
                price_by_currency = {
                    cur: _round_price(price_eur / fx, cur)
                    for cur, fx in config.CURRENCY_FX_TO_EUR.items()
                }
                skus.append(
                    {
                        "sku_id": sku_id,
                        "category": category,
                        "style": style,
                        "color": color,
                        "product_name": f"{style} — {color}",
                        "base_price_eur": price_eur,
                        "price_by_currency": price_by_currency,
                        "demand_weight": cfg["demand_weight"],
                    }
                )
    return skus


@lru_cache(maxsize=1)
def sku_index() -> dict[str, dict]:
    return {s["sku_id"]: s for s in build_catalog()}


def all_sku_ids() -> list[str]:
    return [s["sku_id"] for s in build_catalog()]


def category_demand_weights() -> tuple[list[str], list[float]]:
    """SKU ids and their demand weights, for weighted sampling of what sells."""
    cat = build_catalog()
    return [s["sku_id"] for s in cat], [s["demand_weight"] for s in cat]


def price_for(sku_id: str, currency: str) -> float:
    return sku_index()[sku_id]["price_by_currency"][currency]


if __name__ == "__main__":
    cat = build_catalog()
    print(f"{len(cat)} SKUs across {len(config.CATEGORIES)} categories")
    for s in cat[:5]:
        print(s["sku_id"], s["product_name"], s["base_price_eur"], "EUR")
