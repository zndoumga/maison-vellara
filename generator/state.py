"""
StateStore — the generator's authoritative working memory.

It holds the mutable state that must survive between runs so that the world
evolves coherently: clients accumulate, inventory depletes and replenishes,
after-sales orders progress over days, and returns/corrections can reference
real prior transactions.

Phase 1 uses a local SQLite backend (LocalStateStore). The cloud deployment
(Phase 2) mirrors these same methods against a dedicated Supabase `state`
schema, so generators depend only on this interface — never on the backend.
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
from datetime import date
from typing import Iterable, Optional


class LocalStateStore:
    def __init__(self, state_dir: str):
        os.makedirs(state_dir, exist_ok=True)
        self.path = os.path.join(state_dir, "state.db")
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        c = self.conn
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS seqs (
                name TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                email TEXT, phone TEXT, nationality TEXT,
                country_of_residence TEXT,
                assigned_store_id TEXT, assigned_advisor_id TEXT,
                created_date TEXT, updated_date TEXT,
                record TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_clients_store ON clients(assigned_store_id);
            CREATE INDEX IF NOT EXISTS ix_clients_updated ON clients(updated_date);

            CREATE TABLE IF NOT EXISTS ecom_clients (
                client_id TEXT PRIMARY KEY,
                email TEXT, phone TEXT, country TEXT,
                record TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory_position (
                store_id TEXT, sku_id TEXT,
                qty_on_hand INTEGER, qty_reserved INTEGER, qty_in_transit INTEGER,
                last_replenishment_dt TEXT, reorder_flag INTEGER,
                replenish_eta TEXT,
                PRIMARY KEY (store_id, sku_id)
            );

            CREATE TABLE IF NOT EXISTS after_sales_open (
                repair_id TEXT PRIMARY KEY,
                status TEXT, received_date TEXT,
                record TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recent_transactions (
                transaction_id TEXT PRIMARY KEY,
                store_id TEXT, txn_date TEXT, client_id TEXT,
                currency TEXT, total REAL, returned INTEGER DEFAULT 0,
                record TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_recent_date ON recent_transactions(txn_date);

            CREATE TABLE IF NOT EXISTS recent_ecom_orders (
                order_id TEXT PRIMARY KEY,
                order_date TEXT, returned INTEGER DEFAULT 0,
                record TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_ecom_date ON recent_ecom_orders(order_date);

            CREATE TABLE IF NOT EXISTS partner_stock (
                partner_id TEXT, sku_id TEXT, qty INTEGER,
                PRIMARY KEY (partner_id, sku_id)
            );

            CREATE TABLE IF NOT EXISTS partner_customers (
                partner_id TEXT, customer_ref TEXT,
                record TEXT NOT NULL,
                PRIMARY KEY (partner_id, customer_ref)
            );

            CREATE TABLE IF NOT EXISTS pending_shipments (
                po_number TEXT PRIMARY KEY,
                partner_id TEXT, ship_date TEXT,
                record TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_ship_date ON pending_shipments(ship_date);

            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        c.commit()

    # ---- lifecycle -------------------------------------------------------
    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def get_meta(self, key: str) -> Optional[str]:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    # ---- sequences -------------------------------------------------------
    def next_seq(self, name: str, reset_scope: str | None = None) -> int:
        """
        Next integer in a named sequence. If reset_scope is given (e.g. a
        store+date key), the counter resets when the scope changes — used for
        per-store, per-day receipt numbering.
        """
        if reset_scope is not None:
            name = f"{name}:{reset_scope}"
        row = self.conn.execute("SELECT value FROM seqs WHERE name=?", (name,)).fetchone()
        nxt = (row["value"] if row else 0) + 1
        self.conn.execute(
            "INSERT INTO seqs(name,value) VALUES(?,?) "
            "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
            (name, nxt),
        )
        return nxt

    # ---- clients ---------------------------------------------------------
    def add_client(self, rec: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO clients(client_id,email,phone,nationality,"
            "country_of_residence,assigned_store_id,assigned_advisor_id,"
            "created_date,updated_date,record) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                rec["client_id"], rec.get("email"), rec.get("phone"),
                rec.get("nationality"), rec.get("country_of_residence"),
                rec.get("assigned_store_id"), rec.get("assigned_advisor_id"),
                rec["created_at"][:10], rec["updated_at"][:10], json.dumps(rec),
            ),
        )

    def client_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM clients").fetchone()["n"]

    def sample_existing_client(self, rng: random.Random, store_id: str | None = None) -> Optional[dict]:
        if store_id:
            rows = self.conn.execute(
                "SELECT client_id FROM clients WHERE assigned_store_id=?", (store_id,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT client_id FROM clients").fetchall()
        if not rows:
            return None
        cid = rng.choice(rows)["client_id"]
        return self.get_client(cid)

    def get_client(self, client_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT record FROM clients WHERE client_id=?", (client_id,)
        ).fetchone()
        return json.loads(row["record"]) if row else None

    def touch_client(self, client_id: str, updated_at_iso: str) -> None:
        rec = self.get_client(client_id)
        if not rec:
            return
        rec["updated_at"] = updated_at_iso
        self.add_client(rec)

    def clients_changed_on(self, d: date) -> list[dict]:
        iso = d.isoformat()
        rows = self.conn.execute(
            "SELECT record FROM clients WHERE created_date=? OR updated_date=?",
            (iso, iso),
        ).fetchall()
        return [json.loads(r["record"]) for r in rows]

    # ---- ecom clients ----------------------------------------------------
    def add_ecom_client(self, rec: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO ecom_clients(client_id,email,phone,country,record) "
            "VALUES(?,?,?,?,?)",
            (rec["id"], rec.get("email"), rec.get("phone"), rec.get("country"), json.dumps(rec)),
        )

    def ecom_client_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) n FROM ecom_clients").fetchone()["n"]

    def sample_ecom_client(self, rng: random.Random) -> Optional[dict]:
        rows = self.conn.execute("SELECT client_id FROM ecom_clients").fetchall()
        if not rows:
            return None
        cid = rng.choice(rows)["client_id"]
        row = self.conn.execute(
            "SELECT record FROM ecom_clients WHERE client_id=?", (cid,)
        ).fetchone()
        return json.loads(row["record"])

    # ---- inventory -------------------------------------------------------
    def get_position(self, store_id: str, sku_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM inventory_position WHERE store_id=? AND sku_id=?",
            (store_id, sku_id),
        ).fetchone()
        return dict(row) if row else None

    def upsert_position(self, pos: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO inventory_position(store_id,sku_id,qty_on_hand,"
            "qty_reserved,qty_in_transit,last_replenishment_dt,reorder_flag,replenish_eta) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                pos["store_id"], pos["sku_id"], pos["qty_on_hand"],
                pos["qty_reserved"], pos["qty_in_transit"],
                pos.get("last_replenishment_dt"), int(pos.get("reorder_flag", 0)),
                pos.get("replenish_eta"),
            ),
        )

    def all_positions(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM inventory_position").fetchall()
        return [dict(r) for r in rows]

    def positions_initialised(self) -> bool:
        return self.conn.execute(
            "SELECT COUNT(*) n FROM inventory_position"
        ).fetchone()["n"] > 0

    # ---- after-sales -----------------------------------------------------
    def add_open_order(self, rec: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO after_sales_open(repair_id,status,received_date,record) "
            "VALUES(?,?,?,?)",
            (rec["repair_id"], rec["status"], rec["received_date"], json.dumps(rec)),
        )

    def open_orders(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT record FROM after_sales_open WHERE status != 'collected'"
        ).fetchall()
        return [json.loads(r["record"]) for r in rows]

    def update_open_order(self, rec: dict) -> None:
        if rec["status"] == "collected":
            self.conn.execute(
                "DELETE FROM after_sales_open WHERE repair_id=?", (rec["repair_id"],)
            )
        else:
            self.add_open_order(rec)

    # ---- recent transactions (returns / corrections) ---------------------
    def add_transaction_ref(self, rec: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO recent_transactions(transaction_id,store_id,txn_date,"
            "client_id,currency,total,returned,record) VALUES(?,?,?,?,?,?,0,?)",
            (
                rec["transaction_id"], rec["store_id"], rec["txn_date"],
                rec.get("client_id"), rec["currency"], rec["total"], json.dumps(rec),
            ),
        )

    def sample_recent_sale(
        self, rng: random.Random, store_id: str, min_age_days: int, max_age_days: int, on_date: date
    ) -> Optional[dict]:
        from datetime import timedelta

        hi = (on_date - timedelta(days=min_age_days)).isoformat()
        lo = (on_date - timedelta(days=max_age_days)).isoformat()
        rows = self.conn.execute(
            "SELECT transaction_id FROM recent_transactions "
            "WHERE store_id=? AND returned=0 AND txn_date BETWEEN ? AND ?",
            (store_id, lo, hi),
        ).fetchall()
        if not rows:
            return None
        tid = rng.choice(rows)["transaction_id"]
        row = self.conn.execute(
            "SELECT record FROM recent_transactions WHERE transaction_id=?", (tid,)
        ).fetchone()
        return json.loads(row["record"])

    def mark_returned(self, transaction_id: str) -> None:
        self.conn.execute(
            "UPDATE recent_transactions SET returned=1 WHERE transaction_id=?",
            (transaction_id,),
        )

    def prune_transactions(self, before: date) -> None:
        self.conn.execute(
            "DELETE FROM recent_transactions WHERE txn_date < ?", (before.isoformat(),)
        )

    # ---- recent ecom orders (returns) ------------------------------------
    def add_ecom_order_ref(self, rec: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO recent_ecom_orders(order_id,order_date,returned,record) "
            "VALUES(?,?,0,?)",
            (rec["order_id"], rec["order_date"], json.dumps(rec)),
        )

    def sample_recent_ecom_order(
        self, rng: random.Random, min_age_days: int, max_age_days: int, on_date: date
    ) -> Optional[dict]:
        from datetime import timedelta

        hi = (on_date - timedelta(days=min_age_days)).isoformat()
        lo = (on_date - timedelta(days=max_age_days)).isoformat()
        rows = self.conn.execute(
            "SELECT order_id FROM recent_ecom_orders "
            "WHERE returned=0 AND order_date BETWEEN ? AND ?",
            (lo, hi),
        ).fetchall()
        if not rows:
            return None
        oid = rng.choice(rows)["order_id"]
        row = self.conn.execute(
            "SELECT record FROM recent_ecom_orders WHERE order_id=?", (oid,)
        ).fetchone()
        return json.loads(row["record"])

    def mark_ecom_returned(self, order_id: str) -> None:
        self.conn.execute(
            "UPDATE recent_ecom_orders SET returned=1 WHERE order_id=?", (order_id,)
        )

    def prune_ecom_orders(self, before: date) -> None:
        self.conn.execute(
            "DELETE FROM recent_ecom_orders WHERE order_date < ?", (before.isoformat(),)
        )

    # ---- partner (wholesale) stock & customers ---------------------------
    def get_partner_stock(self, partner_id: str, sku_id: str) -> Optional[int]:
        row = self.conn.execute(
            "SELECT qty FROM partner_stock WHERE partner_id=? AND sku_id=?",
            (partner_id, sku_id),
        ).fetchone()
        return row["qty"] if row else None

    def set_partner_stock(self, partner_id: str, sku_id: str, qty: int) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO partner_stock(partner_id,sku_id,qty) VALUES(?,?,?)",
            (partner_id, sku_id, qty),
        )

    def partner_assortment(self, partner_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT sku_id FROM partner_stock WHERE partner_id=?", (partner_id,)
        ).fetchall()
        return [r["sku_id"] for r in rows]

    def add_partner_customer(self, partner_id: str, customer_ref: str, rec: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO partner_customers(partner_id,customer_ref,record) "
            "VALUES(?,?,?)",
            (partner_id, customer_ref, json.dumps(rec)),
        )

    def sample_partner_customer(self, rng: random.Random, partner_id: str) -> Optional[dict]:
        rows = self.conn.execute(
            "SELECT record FROM partner_customers WHERE partner_id=?", (partner_id,)
        ).fetchall()
        if not rows:
            return None
        return json.loads(rng.choice(rows)["record"])

    def partner_customer_count(self, partner_id: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) n FROM partner_customers WHERE partner_id=?", (partner_id,)
        ).fetchone()["n"]

    # ---- pending wholesale shipments -------------------------------------
    def add_pending_shipment(self, po_number: str, partner_id: str, ship_date: str, rec: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO pending_shipments(po_number,partner_id,ship_date,record) "
            "VALUES(?,?,?,?)",
            (po_number, partner_id, ship_date, json.dumps(rec)),
        )

    def due_shipments(self, d: date) -> list[dict]:
        rows = self.conn.execute(
            "SELECT record FROM pending_shipments WHERE ship_date <= ?", (d.isoformat(),)
        ).fetchall()
        return [json.loads(r["record"]) for r in rows]

    def remove_pending_shipment(self, po_number: str) -> None:
        self.conn.execute("DELETE FROM pending_shipments WHERE po_number=?", (po_number,))
