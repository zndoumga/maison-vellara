"""
SupabaseStateStore — cloud equivalent of LocalStateStore.

Implements the exact same interface, backed by the generator_state schema in
Supabase. The generators never import this directly — run.py selects the right
store based on SINK_MODE and passes it in.
"""
from __future__ import annotations

import json
import os
import random
from datetime import date, timedelta
from typing import Optional

from supabase import create_client, Client


def _client() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


class SupabaseStateStore:
    def __init__(self):
        self.sb = _client()

    def _gs(self, table: str):
        return self.sb.schema("generator_state").table(table)

    def commit(self) -> None:
        pass  # Supabase writes are immediate

    def close(self) -> None:
        pass

    # ---- meta ------------------------------------------------------------
    def get_meta(self, key: str) -> Optional[str]:
        r = self._gs("meta").select("value").eq("key", key).maybe_single().execute()
        return r.data["value"] if r.data else None

    def set_meta(self, key: str, value: str) -> None:
        self._gs("meta").upsert({"key": key, "value": value}).execute()

    # ---- sequences -------------------------------------------------------
    def next_seq(self, name: str, reset_scope: str | None = None) -> int:
        if reset_scope is not None:
            name = f"{name}:{reset_scope}"
        r = self._gs("seqs").select("value").eq("name", name).maybe_single().execute()
        nxt = (r.data["value"] if r.data else 0) + 1
        self._gs("seqs").upsert({"name": name, "value": nxt}).execute()
        return nxt

    # ---- clients ---------------------------------------------------------
    def add_client(self, rec: dict) -> None:
        self._gs("clients").upsert({
            "client_id": rec["client_id"],
            "email": rec.get("email"),
            "phone": rec.get("phone"),
            "nationality": rec.get("nationality"),
            "country_of_residence": rec.get("country_of_residence"),
            "assigned_store_id": rec.get("assigned_store_id"),
            "assigned_advisor_id": rec.get("assigned_advisor_id"),
            "created_date": rec["created_at"][:10],
            "updated_date": rec["updated_at"][:10],
            "record": rec,
        }).execute()

    def client_count(self) -> int:
        r = self._gs("clients").select("client_id", count="exact").execute()
        return r.count or 0

    def sample_existing_client(self, rng: random.Random, store_id: str | None = None) -> Optional[dict]:
        q = self._gs("clients").select("client_id")
        if store_id:
            q = q.eq("assigned_store_id", store_id)
        r = q.limit(200).execute()
        if not r.data:
            return None
        cid = rng.choice(r.data)["client_id"]
        return self.get_client(cid)

    def get_client(self, client_id: str) -> Optional[dict]:
        r = self._gs("clients").select("record").eq("client_id", client_id).maybe_single().execute()
        return r.data["record"] if r.data else None

    def touch_client(self, client_id: str, updated_at_iso: str) -> None:
        rec = self.get_client(client_id)
        if not rec:
            return
        rec["updated_at"] = updated_at_iso
        self.add_client(rec)

    def clients_changed_on(self, d: date) -> list[dict]:
        iso = d.isoformat()
        r = self._gs("clients").select("record").or_(
            f"created_date.eq.{iso},updated_date.eq.{iso}"
        ).execute()
        return [row["record"] for row in (r.data or [])]

    # ---- ecom clients ----------------------------------------------------
    def add_ecom_client(self, rec: dict) -> None:
        self._gs("ecom_clients").upsert({
            "client_id": rec["id"],
            "email": rec.get("email"),
            "phone": rec.get("phone"),
            "country": rec.get("country"),
            "record": rec,
        }).execute()

    def ecom_client_count(self) -> int:
        r = self._gs("ecom_clients").select("client_id", count="exact").execute()
        return r.count or 0

    def sample_ecom_client(self, rng: random.Random) -> Optional[dict]:
        r = self._gs("ecom_clients").select("client_id").limit(200).execute()
        if not r.data:
            return None
        cid = rng.choice(r.data)["client_id"]
        row = self._gs("ecom_clients").select("record").eq("client_id", cid).maybe_single().execute()
        return row.data["record"] if row.data else None

    # ---- inventory -------------------------------------------------------
    def get_position(self, store_id: str, sku_id: str) -> Optional[dict]:
        r = self.sb.schema("inventory").table("positions").select("*").eq("store_id", store_id).eq("sku_id", sku_id).maybe_single().execute()
        return dict(r.data) if r.data else None

    def upsert_position(self, pos: dict) -> None:
        self.sb.schema("inventory").table("positions").upsert({
            "store_id": pos["store_id"], "sku_id": pos["sku_id"],
            "qty_on_hand": pos["qty_on_hand"], "qty_reserved": pos.get("qty_reserved", 0),
            "qty_in_transit": pos.get("qty_in_transit", 0),
            "last_replenishment_dt": pos.get("last_replenishment_dt"),
            "reorder_flag": bool(pos.get("reorder_flag", False)),
            "replenish_eta": pos.get("replenish_eta"),
        }).execute()

    def all_positions(self) -> list[dict]:
        r = self.sb.schema("inventory").table("positions").select("*").execute()
        return [dict(row) for row in (r.data or [])]

    def positions_initialised(self) -> bool:
        r = self.sb.schema("inventory").table("positions").select("store_id", count="exact").limit(1).execute()
        return (r.count or 0) > 0

    # ---- after-sales -----------------------------------------------------
    def add_open_order(self, rec: dict) -> None:
        self._gs("after_sales_open").upsert({
            "repair_id": rec["repair_id"],
            "status": rec["status"],
            "received_date": rec["received_date"],
            "record": rec,
        }).execute()

    def open_orders(self) -> list[dict]:
        r = self._gs("after_sales_open").select("record").neq("status", "collected").execute()
        return [row["record"] for row in (r.data or [])]

    def update_open_order(self, rec: dict) -> None:
        if rec["status"] == "collected":
            self._gs("after_sales_open").delete().eq("repair_id", rec["repair_id"]).execute()
        else:
            self.add_open_order(rec)

    # ---- recent transactions ---------------------------------------------
    def add_transaction_ref(self, rec: dict) -> None:
        self._gs("recent_transactions").upsert({
            "transaction_id": rec["transaction_id"],
            "store_id": rec["store_id"],
            "txn_date": rec["txn_date"],
            "client_id": rec.get("client_id"),
            "currency": rec["currency"],
            "total": rec["total"],
            "returned": False,
            "record": rec,
        }).execute()

    def sample_recent_sale(self, rng: random.Random, store_id: str, min_age_days: int, max_age_days: int, on_date: date) -> Optional[dict]:
        hi = (on_date - timedelta(days=min_age_days)).isoformat()
        lo = (on_date - timedelta(days=max_age_days)).isoformat()
        r = self._gs("recent_transactions").select("transaction_id").eq("store_id", store_id).eq("returned", False).gte("txn_date", lo).lte("txn_date", hi).limit(100).execute()
        if not r.data:
            return None
        tid = rng.choice(r.data)["transaction_id"]
        row = self._gs("recent_transactions").select("record").eq("transaction_id", tid).maybe_single().execute()
        return row.data["record"] if row.data else None

    def mark_returned(self, transaction_id: str) -> None:
        self._gs("recent_transactions").update({"returned": True}).eq("transaction_id", transaction_id).execute()

    def prune_transactions(self, before: date) -> None:
        self._gs("recent_transactions").delete().lt("txn_date", before.isoformat()).execute()

    # ---- recent ecom orders ----------------------------------------------
    def add_ecom_order_ref(self, rec: dict) -> None:
        self._gs("recent_ecom_orders").upsert({
            "order_id": rec["order_id"],
            "order_date": rec["order_date"],
            "returned": False,
            "record": rec,
        }).execute()

    def sample_recent_ecom_order(self, rng: random.Random, min_age_days: int, max_age_days: int, on_date: date) -> Optional[dict]:
        hi = (on_date - timedelta(days=min_age_days)).isoformat()
        lo = (on_date - timedelta(days=max_age_days)).isoformat()
        r = self._gs("recent_ecom_orders").select("order_id").eq("returned", False).gte("order_date", lo).lte("order_date", hi).limit(100).execute()
        if not r.data:
            return None
        oid = rng.choice(r.data)["order_id"]
        row = self._gs("recent_ecom_orders").select("record").eq("order_id", oid).maybe_single().execute()
        return row.data["record"] if row.data else None

    def mark_ecom_returned(self, order_id: str) -> None:
        self._gs("recent_ecom_orders").update({"returned": True}).eq("order_id", order_id).execute()

    def prune_ecom_orders(self, before: date) -> None:
        self._gs("recent_ecom_orders").delete().lt("order_date", before.isoformat()).execute()

    # ---- partner stock & customers ---------------------------------------
    def get_partner_stock(self, partner_id: str, sku_id: str) -> Optional[int]:
        r = self._gs("partner_stock").select("qty").eq("partner_id", partner_id).eq("sku_id", sku_id).maybe_single().execute()
        return r.data["qty"] if r.data else None

    def set_partner_stock(self, partner_id: str, sku_id: str, qty: int) -> None:
        self._gs("partner_stock").upsert({"partner_id": partner_id, "sku_id": sku_id, "qty": qty}).execute()

    def partner_assortment(self, partner_id: str) -> list[str]:
        r = self._gs("partner_stock").select("sku_id").eq("partner_id", partner_id).execute()
        return [row["sku_id"] for row in (r.data or [])]

    def add_partner_customer(self, partner_id: str, customer_ref: str, rec: dict) -> None:
        self._gs("partner_customers").upsert({"partner_id": partner_id, "customer_ref": customer_ref, "record": rec}).execute()

    def sample_partner_customer(self, rng: random.Random, partner_id: str) -> Optional[dict]:
        r = self._gs("partner_customers").select("record").eq("partner_id", partner_id).limit(200).execute()
        if not r.data:
            return None
        return rng.choice(r.data)["record"]

    def partner_customer_count(self, partner_id: str) -> int:
        r = self._gs("partner_customers").select("partner_id", count="exact").eq("partner_id", partner_id).execute()
        return r.count or 0

    # ---- pending shipments -----------------------------------------------
    def add_pending_shipment(self, po_number: str, partner_id: str, ship_date: str, rec: dict) -> None:
        self._gs("pending_shipments").upsert({"po_number": po_number, "partner_id": partner_id, "ship_date": ship_date, "record": rec}).execute()

    def due_shipments(self, d: date) -> list[dict]:
        r = self._gs("pending_shipments").select("record").lte("ship_date", d.isoformat()).execute()
        return [row["record"] for row in (r.data or [])]

    def remove_pending_shipment(self, po_number: str) -> None:
        self._gs("pending_shipments").delete().eq("po_number", po_number).execute()
