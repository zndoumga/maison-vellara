"""
E-commerce endpoints — serve Shopify-style nested JSON from Firebase.

  GET /ecom/orders?date=YYYY-MM-DD
  GET /ecom/events?date=YYYY-MM-DD
  GET /ecom/returns?date=YYYY-MM-DD

Returns 404 when no data exists for that date (mirrors a portal outage or a
date before the first order). Fabric's HTTP connector should be configured with
a 404 = empty result policy.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import require_api_key
from firebase_client import db

router = APIRouter(prefix="/ecom", dependencies=[Depends(require_api_key)])


def _fetch(collection: str, date: str, key: str):
    doc = db().collection(collection).document(date).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"No {key} data for {date}")
    return doc.to_dict().get(key, [])


@router.get("/orders")
def get_orders(date: str = Query(..., description="YYYY-MM-DD")):
    return _fetch("ecom_orders", date, "orders")


@router.get("/events")
def get_events(date: str = Query(..., description="YYYY-MM-DD")):
    return _fetch("ecom_events", date, "events")


@router.get("/returns")
def get_returns(date: str = Query(..., description="YYYY-MM-DD")):
    return _fetch("ecom_returns", date, "returns")
