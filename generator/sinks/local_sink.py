"""
LocalSink — writes generated raw data to the local filesystem, laid out the
same way the cloud backends will store it. This lets the whole generator run
and be inspected with zero cloud credentials (Phase 1).

Layout under OUTPUT_DIR:
  boutiques/pos/date=YYYY-MM-DD/transactions.csv
  boutiques/crm/date=YYYY-MM-DD/clients.csv
  boutiques/inventory/date=YYYY-MM-DD/snapshots.csv
  boutiques/after_sales/date=YYYY-MM-DD/orders.csv
  boutiques/masters/*.csv
  online/orders/date=YYYY-MM-DD/orders.json        (array of nested order docs)
  online/events/date=YYYY-MM-DD/events.json
  online/returns/date=YYYY-MM-DD/returns.json
  wholesale/<PARTNER>/po/<file>.csv                (raw partner dialect, as-is)
  wholesale/<PARTNER>/shipments/<file>.csv
  wholesale/<PARTNER>/sellthrough/date=YYYY-MM-DD.json
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import date


class LocalSink:
    def __init__(self, output_dir: str):
        self.root = output_dir
        os.makedirs(self.root, exist_ok=True)
        self.counts: dict[str, int] = {}

    # ---- helpers ---------------------------------------------------------
    def _path(self, *parts: str) -> str:
        p = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    def _bump(self, key: str, n: int) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def _write_csv(self, path: str, rows: list[dict]) -> None:
        if not rows:
            # still emit an empty file so downstream sees the partition exists
            open(path, "w", encoding="utf-8").close()
            return
        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    def _write_json(self, path: str, obj) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    # ---- Source 1: boutiques --------------------------------------------
    def write_pos(self, d: date, rows: list[dict]) -> None:
        self._write_csv(self._path("boutiques", "pos", f"date={d.isoformat()}", "transactions.csv"), rows)
        self._bump("pos", len(rows))

    def write_clients(self, d: date, rows: list[dict]) -> None:
        self._write_csv(self._path("boutiques", "crm", f"date={d.isoformat()}", "clients.csv"), rows)
        self._bump("clients", len(rows))

    def write_inventory(self, d: date, rows: list[dict]) -> None:
        self._write_csv(self._path("boutiques", "inventory", f"date={d.isoformat()}", "snapshots.csv"), rows)
        self._bump("inventory", len(rows))

    def write_after_sales(self, d: date, rows: list[dict]) -> None:
        self._write_csv(self._path("boutiques", "after_sales", f"date={d.isoformat()}", "orders.csv"), rows)
        self._bump("after_sales", len(rows))

    def write_masters(self, masters: dict[str, list[dict]]) -> None:
        for name, rows in masters.items():
            self._write_csv(self._path("boutiques", "masters", f"{name}.csv"), rows)

    # ---- Source 2: online store -----------------------------------------
    def write_ecom_orders(self, d: date, docs: list[dict]) -> None:
        self._write_json(self._path("online", "orders", f"date={d.isoformat()}", "orders.json"), docs)
        self._bump("ecom_orders", len(docs))

    def write_ecom_events(self, d: date, docs: list[dict]) -> None:
        self._write_json(self._path("online", "events", f"date={d.isoformat()}", "events.json"), docs)
        self._bump("ecom_events", len(docs))

    def write_ecom_returns(self, d: date, docs: list[dict]) -> None:
        self._write_json(self._path("online", "returns", f"date={d.isoformat()}", "returns.json"), docs)
        self._bump("ecom_returns", len(docs))

    # ---- Source 3: wholesale --------------------------------------------
    def write_wholesale_file(self, partner_id: str, kind: str, filename: str, content: str) -> None:
        path = self._path("wholesale", partner_id, kind, filename)
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write(content)
        self._bump(f"wholesale_{kind}", 1)

    def write_sellthrough(self, partner_id: str, d: date, doc: dict) -> None:
        path = self._path("wholesale", partner_id, "sellthrough", f"date={d.isoformat()}.json")
        self._write_json(path, doc)
        self._bump("sellthrough", 1)

    def close(self) -> None:
        pass


def make_empty_csv_string(rows: list[dict]) -> str:
    """Utility used by wholesale generators to render rows to a CSV string."""
    if not rows:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
