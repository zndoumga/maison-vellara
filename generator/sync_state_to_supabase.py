"""
One-time: push the local backfill state (SQLite) into the Supabase
generator_state schema (and inventory.positions), so the Railway nightly
scheduler can continue the same evolving world from where the backfill ended.

Run AFTER a clean local backfill:
    python sync_state_to_supabase.py
"""
from __future__ import annotations

import json
import os
import sqlite3

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

STATE_DB = os.path.join(os.environ.get("STATE_DIR", "./state"), "state.db")
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def rows(conn, query):
    cur = conn.execute(query)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def chunk(lst, n=500):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def push(schema, table, data, transform):
    if not data:
        print(f"  {schema}.{table}: nothing to push")
        return
    payload = [transform(r) for r in data]
    for batch in chunk(payload):
        sb.schema(schema).table(table).upsert(batch).execute()
    print(f"  {schema}.{table}: {len(payload)} rows")


def main():
    conn = sqlite3.connect(STATE_DB)
    print(f"Reading {STATE_DB}")

    push("generator_state", "seqs", rows(conn, "SELECT * FROM seqs"),
         lambda r: {"name": r["name"], "value": r["value"]})

    push("generator_state", "clients", rows(conn, "SELECT * FROM clients"),
         lambda r: {"client_id": r["client_id"], "email": r["email"], "phone": r["phone"],
                    "nationality": r["nationality"], "country_of_residence": r["country_of_residence"],
                    "assigned_store_id": r["assigned_store_id"], "assigned_advisor_id": r["assigned_advisor_id"],
                    "created_date": r["created_date"], "updated_date": r["updated_date"],
                    "record": json.loads(r["record"])})

    push("generator_state", "ecom_clients", rows(conn, "SELECT * FROM ecom_clients"),
         lambda r: {"client_id": r["client_id"], "email": r["email"], "phone": r["phone"],
                    "country": r["country"], "record": json.loads(r["record"])})

    push("inventory", "positions", rows(conn, "SELECT * FROM inventory_position"),
         lambda r: {"store_id": r["store_id"], "sku_id": r["sku_id"], "qty_on_hand": r["qty_on_hand"],
                    "qty_reserved": r["qty_reserved"], "qty_in_transit": r["qty_in_transit"],
                    "last_replenishment_dt": r["last_replenishment_dt"],
                    "reorder_flag": bool(r["reorder_flag"]), "replenish_eta": r["replenish_eta"]})

    push("generator_state", "after_sales_open", rows(conn, "SELECT * FROM after_sales_open"),
         lambda r: {"repair_id": r["repair_id"], "status": r["status"],
                    "received_date": r["received_date"], "record": json.loads(r["record"])})

    push("generator_state", "recent_transactions", rows(conn, "SELECT * FROM recent_transactions"),
         lambda r: {"transaction_id": r["transaction_id"], "store_id": r["store_id"], "txn_date": r["txn_date"],
                    "client_id": r["client_id"], "currency": r["currency"], "total": r["total"],
                    "returned": bool(r["returned"]), "record": json.loads(r["record"])})

    push("generator_state", "recent_ecom_orders", rows(conn, "SELECT * FROM recent_ecom_orders"),
         lambda r: {"order_id": r["order_id"], "order_date": r["order_date"],
                    "returned": bool(r["returned"]), "record": json.loads(r["record"])})

    push("generator_state", "partner_stock", rows(conn, "SELECT * FROM partner_stock"),
         lambda r: {"partner_id": r["partner_id"], "sku_id": r["sku_id"], "qty": r["qty"]})

    push("generator_state", "partner_customers", rows(conn, "SELECT * FROM partner_customers"),
         lambda r: {"partner_id": r["partner_id"], "customer_ref": r["customer_ref"],
                    "record": json.loads(r["record"])})

    push("generator_state", "pending_shipments", rows(conn, "SELECT * FROM pending_shipments"),
         lambda r: {"po_number": r["po_number"], "partner_id": r["partner_id"],
                    "ship_date": r["ship_date"], "record": json.loads(r["record"])})

    push("generator_state", "meta", rows(conn, "SELECT * FROM meta"),
         lambda r: {"key": r["key"], "value": r["value"]})

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
