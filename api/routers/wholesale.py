"""
Wholesale partner portal endpoints — each partner returns its own JSON shape.

  GET /wholesale/glf/sellthrough?date=YYYY-MM-DD  → GLF object shape
  GET /wholesale/lbm/sellthrough?date=YYYY-MM-DD  → LBM object shape
  GET /wholesale/prt/sellthrough?date=YYYY-MM-DD  → PRT array shape

Returns 404 on portal outage days (no document stored) — realistic and expected.
The three responses are intentionally different structures, mirroring real
department-store partner portal APIs. Fabric/dbt normalises them downstream.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import require_api_key
from firebase_client import db

router = APIRouter(prefix="/wholesale", dependencies=[Depends(require_api_key)])

VALID_PARTNERS = {"glf", "lbm", "prt"}


@router.get("/{partner}/sellthrough")
def get_sellthrough(partner: str, date: str = Query(..., description="YYYY-MM-DD")):
    partner = partner.lower()
    if partner not in VALID_PARTNERS:
        raise HTTPException(status_code=404, detail=f"Unknown partner: {partner}")

    doc = (
        db()
        .collection("wholesale_sellthrough")
        .document(partner.upper())
        .collection("daily")
        .document(date)
        .get()
    )
    if not doc.exists:
        raise HTTPException(
            status_code=404,
            detail=f"No sell-through data for {partner.upper()} on {date} — portal may be down",
        )

    return doc.to_dict().get("data", {})
