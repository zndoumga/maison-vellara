"""
Wholesale purchase orders & shipment confirmations — file-based (EDI-style).

Each partner sends/receives files in its **own independent dialect**: different
column names, delimiters, date formats and decimal separators. There is no
shared schema. Files are irregular (a few per partner per month).

  GLF (Galeries Lafayette): comma-delimited, UPPER FR headers, DD/MM/YYYY, dot decimals
  LBM (Le Bon Marché):      comma-delimited, lower en/fr headers, ISO dates, dot decimals
  PRT (Printemps):          semicolon-delimited, short UPPER keys, DDMMYYYY, comma decimals

PO places stock on order; a shipment confirmation (sometimes partial) lands a
few days later and increments the partner's stock (used by sell-through).
"""
from __future__ import annotations

import io
import random
from datetime import date, timedelta

import catalog
import config
from utils.rng import chance

WHOLESALE_PRICE = lambda sku: round(catalog.sku_index()[sku]["price_by_currency"]["EUR"] * config.WHOLESALE_PRICE_FACTOR / 10) * 10

_PARTNERS = [p["partner_id"] for p in config.WHOLESALE_PARTNERS]


# ---------------------------------------------------------------------------
# assortment / stock setup
# ---------------------------------------------------------------------------
def ensure_assortment(state) -> None:
    if all(state.partner_assortment(p) for p in _PARTNERS):
        return
    all_skus = catalog.all_sku_ids()
    for partner in _PARTNERS:
        if state.partner_assortment(partner):
            continue
        rng = random.Random(f"assort-{partner}")
        k = int(len(all_skus) * config.WHOLESALE_ASSORTMENT_RATE)
        chosen = rng.sample(all_skus, k)
        for sku in chosen:
            state.set_partner_stock(partner, sku, 0)


# ---------------------------------------------------------------------------
# date / number helpers
# ---------------------------------------------------------------------------
def _glf_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")

def _lbm_date(d: date) -> str:
    return d.isoformat()

def _prt_date(d: date) -> str:
    return d.strftime("%d%m%Y")

def _comma_dec(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


def _csv(rows: list[dict], delimiter: str) -> str:
    import csv
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter=delimiter)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PO renderers (one per dialect)
# ---------------------------------------------------------------------------
def _render_po(partner: str, po_number: str, order_d: date, delivery_d: date, lines: list[dict]) -> str:
    if partner == "GLF":
        rows = [{
            "PO_NUMBER": po_number,
            "DATE_COMMANDE": _glf_date(order_d),
            "DATE_LIVRAISON_SOUHAITEE": _glf_date(delivery_d),
            "CODE_ARTICLE": l["sku"],
            "DESIGNATION": l["name"],
            "QUANTITE": l["qty"],
            "PRIX_UNITAIRE_HT": f"{l['price']:.2f}",
            "DEVISE": "EUR",
        } for l in lines]
        return _csv(rows, ",")
    if partner == "LBM":
        rows = [{
            "reference": po_number,
            "order_date": _lbm_date(order_d),
            "requested_delivery": _lbm_date(delivery_d),
            "sku": l["sku"],
            "description": l["name"],
            "quantity": l["qty"],
            "unit_price": f"{l['price']:.2f}",
            "currency": "EUR",
        } for l in lines]
        return _csv(rows, ",")
    # PRT
    rows = [{
        "NUM_CMD": po_number,
        "DT_CMD": _prt_date(order_d),
        "DT_LIV": _prt_date(delivery_d),
        "ART": l["sku"],
        "QTE": l["qty"],
        "PU": _comma_dec(l["price"]),
    } for l in lines]
    return _csv(rows, ";")


def _render_shipment(partner: str, bl_number: str, po_number: str, ship_d: date, lines: list[dict]) -> str:
    if partner == "GLF":
        rows = [{
            "BL_NUMBER": bl_number, "PO_NUMBER": po_number,
            "DATE_EXPEDITION": _glf_date(ship_d), "CODE_ARTICLE": l["sku"],
            "QUANTITE_LIVREE": l["delivered"], "STATUT": l["status"],
        } for l in lines]
        return _csv(rows, ",")
    if partner == "LBM":
        rows = [{
            "shipment_ref": bl_number, "order_reference": po_number,
            "ship_date": _lbm_date(ship_d), "sku": l["sku"],
            "delivered_qty": l["delivered"], "status": l["status"],
        } for l in lines]
        return _csv(rows, ",")
    rows = [{
        "NUM_BL": bl_number, "NUM_CMD": po_number, "DT_EXP": _prt_date(ship_d),
        "ART": l["sku"], "QTE_LIV": l["delivered"], "ETAT": l["status"],
    } for l in lines]
    return _csv(rows, ";")


def _po_number(state, partner: str, d: date) -> str:
    seq = state.next_seq(f"po_{partner}")
    if partner == "GLF":
        return f"GLF-{d.year}-{seq:04d}"
    if partner == "LBM":
        return f"LBM{d.strftime('%Y%m%d')}{seq:03d}"
    return f"PRT-{d.strftime('%d%m%y')}-{seq:03d}"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def generate(d: date, state, rng: random.Random) -> list[tuple[str, str, str, str]]:
    """Return list of (partner_id, kind, filename, content)."""
    ensure_assortment(state)
    files: list[tuple[str, str, str, str]] = []

    # 1) fulfil due shipments
    for pending in state.due_shipments(d):
        partner = pending["partner_id"]
        po_number = pending["po_number"]
        bl_seq = state.next_seq(f"bl_{partner}")
        bl_number = f"BL-{partner}-{d.strftime('%Y%m%d')}-{bl_seq:03d}"
        ship_lines = []
        for l in pending["lines"]:
            # occasional partial delivery
            delivered = l["qty"] if not chance(rng, 0.08) else max(1, l["qty"] - rng.randint(1, l["qty"]))
            status = "DELIVERED" if delivered == l["qty"] else "PARTIAL"
            ship_lines.append({"sku": l["sku"], "delivered": delivered, "status": status})
            cur = state.get_partner_stock(partner, l["sku"]) or 0
            state.set_partner_stock(partner, l["sku"], cur + delivered)
        content = _render_shipment(partner, bl_number, po_number, d, ship_lines)
        files.append((partner, "shipments", f"{bl_number}.csv", content))
        state.remove_pending_shipment(po_number)

    # 2) maybe place new POs (≈2-4 per partner per month → ~0.12/day)
    for partner in _PARTNERS:
        if not chance(rng, 0.12):
            continue
        assortment = state.partner_assortment(partner)
        if not assortment:
            continue
        n_lines = rng.randint(5, 15)
        skus = rng.sample(assortment, min(n_lines, len(assortment)))
        po_number = _po_number(state, partner, d)
        delivery_d = d + timedelta(days=rng.randint(10, 20))
        lines = []
        for sku in skus:
            s = catalog.sku_index()[sku]
            lines.append({
                "sku": sku, "name": s["product_name"], "qty": rng.randint(2, 8),
                "price": WHOLESALE_PRICE(sku),
            })
        content = _render_po(partner, po_number, d, delivery_d, lines)
        files.append((partner, "po", f"{po_number}.csv", content))

        ship_date = (d + timedelta(days=rng.randint(5, 10))).isoformat()
        state.add_pending_shipment(po_number, partner, ship_date,
                                   {"partner_id": partner, "po_number": po_number, "lines": lines})

    return files
