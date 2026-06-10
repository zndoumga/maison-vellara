"""
SupabaseSink — writes boutique source data (POS, CRM, inventory, after-sales,
masters) to Supabase Postgres via the supabase-py client.

Idempotency strategy: delete rows for the date, then insert fresh. This means
re-running a day is safe and produces identical data (deterministic seeds).

The generator_state schema is read/written by SupabaseStateStore (state.py),
not by this sink.
"""
from __future__ import annotations

import os
from datetime import date

from supabase import create_client, Client


def _client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def _chunk(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class SupabaseSink:
    def __init__(self):
        self.sb = _client()

    def _upsert(self, schema: str, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        full = f"{schema}.{table}"
        for batch in _chunk(rows, 500):
            self.sb.schema(schema).table(table).upsert(batch).execute()

    def _delete_by_date(self, schema: str, table: str, date_col: str, d: date) -> None:
        self.sb.schema(schema).table(table).delete().eq(date_col, d.isoformat()).execute()

    # ---- masters (idempotent overwrite) ----------------------------------
    def write_masters(self, masters: dict[str, list[dict]]) -> None:
        mapping = {
            "stores": ("ref", "stores"),
            "advisors": ("ref", "advisors"),
            "technicians": ("ref", "technicians"),
            "products": ("ref", "products"),
            "wholesale_partners": ("ref", "wholesale_partners"),
        }
        for name, rows in masters.items():
            if name in mapping:
                schema, table = mapping[name]
                self._upsert(schema, table, rows)

    # ---- POS -------------------------------------------------------------
    def write_pos(self, d: date, rows: list[dict]) -> None:
        self._delete_by_date("pos", "transactions", "transaction_date", d)
        if rows:
            # coerce None strings to None, strip empty strings
            cleaned = []
            for r in rows:
                cleaned.append({k: (v if v != "" else None) for k, v in r.items()})
            self._upsert("pos", "transactions", cleaned)

    # ---- CRM -------------------------------------------------------------
    def write_clients(self, d: date, rows: list[dict]) -> None:
        if not rows:
            return
        for batch in _chunk(rows, 500):
            self.sb.schema("crm").table("clients").upsert(
                batch, on_conflict="client_id,updated_at"
            ).execute()

    # ---- Inventory -------------------------------------------------------
    def write_inventory(self, d: date, rows: list[dict]) -> None:
        # Snapshots are append-only; delete today's then re-insert
        self.sb.schema("inventory").table("snapshots").delete().filter(
            "snapshot_ts", "gte", f"{d.isoformat()}T00:00:00Z"
        ).filter(
            "snapshot_ts", "lte", f"{d.isoformat()}T23:59:59Z"
        ).execute()
        self._upsert("inventory", "snapshots", rows)

    # ---- After-sales -----------------------------------------------------
    def write_after_sales(self, d: date, rows: list[dict]) -> None:
        if not rows:
            return
        for batch in _chunk(rows, 500):
            self.sb.schema("after_sales").table("orders").upsert(
                batch, on_conflict="repair_id,updated_date"
            ).execute()

    # ---- Ecom (not stored in Supabase — Firebase/FastAPI handles these) --
    def write_ecom_orders(self, d: date, docs: list[dict]) -> None:
        pass

    def write_ecom_events(self, d: date, docs: list[dict]) -> None:
        pass

    def write_ecom_returns(self, d: date, docs: list[dict]) -> None:
        pass

    # ---- Wholesale (not stored in Supabase — Blob/FastAPI handles these) -
    def write_wholesale_file(self, partner_id: str, kind: str, filename: str, content: str) -> None:
        pass

    def write_sellthrough(self, partner_id: str, d: date, doc: dict) -> None:
        pass

    def close(self) -> None:
        pass
