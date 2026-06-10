"""
FirebaseSink — writes online store data (orders, events, returns) and wholesale
sell-through documents to Firebase Firestore.

Collection layout — one document per day, data stored as an array:
  ecom_orders/{date}        → { date, orders: [...] }
  ecom_events/{date}        → { date, events: [...] }
  ecom_returns/{date}       → { date, returns: [...] }
  wholesale_sellthrough/{partner_id}/daily/{date}  → { data, partner_id, date }

Storing per-day arrays rather than per-record documents keeps writes within
Firebase's free tier (3 writes/day vs 3000+/day for individual documents) and
mirrors how a real API export endpoint works — you always fetch a full day.
"""
from __future__ import annotations

import os
from datetime import date

import firebase_admin
from firebase_admin import credentials, firestore


def _ensure_init():
    if not firebase_admin._apps:
        raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if raw:
            import json
            cred = credentials.Certificate(json.loads(raw))
        else:
            cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "./firebase-service-account.json")
            cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)


def _db():
    _ensure_init()
    return firestore.client()


class FirebaseSink:
    def __init__(self):
        _ensure_init()

    def _set_day(self, collection: str, d: date, payload: dict) -> None:
        _db().collection(collection).document(d.isoformat()).set(payload)

    # ---- Ecom orders -----------------------------------------------------
    def write_ecom_orders(self, d: date, docs: list[dict]) -> None:
        self._set_day("ecom_orders", d, {"date": d.isoformat(), "orders": docs})

    # ---- Ecom events -----------------------------------------------------
    def write_ecom_events(self, d: date, docs: list[dict]) -> None:
        self._set_day("ecom_events", d, {"date": d.isoformat(), "events": docs})

    # ---- Ecom returns ----------------------------------------------------
    def write_ecom_returns(self, d: date, docs: list[dict]) -> None:
        self._set_day("ecom_returns", d, {"date": d.isoformat(), "returns": docs})

    # ---- Wholesale sell-through ------------------------------------------
    def write_sellthrough(self, partner_id: str, d: date, doc: dict) -> None:
        _db().collection("wholesale_sellthrough").document(partner_id).collection("daily").document(d.isoformat()).set(
            {"data": doc, "partner_id": partner_id, "date": d.isoformat()}
        )

    # ---- Not handled by this sink ----------------------------------------
    def write_pos(self, d, rows): pass
    def write_clients(self, d, rows): pass
    def write_inventory(self, d, rows): pass
    def write_after_sales(self, d, rows): pass
    def write_masters(self, masters): pass
    def write_wholesale_file(self, partner_id, kind, filename, content): pass

    def close(self) -> None:
        pass
