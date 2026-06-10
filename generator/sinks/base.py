"""
Sink interface.

A sink is the *output* destination for generated raw data — the thing that
stands in for where each source system lands its exports. Generators never
touch a backend directly; they hand finished records to a sink.

Three concrete sinks exist:
  - LocalSink    (Phase 1) writes files under OUTPUT_DIR mirroring the cloud layout
  - SupabaseSink (Phase 2) writes boutique tables via the Supabase client
  - FirebaseSink (Phase 2) writes ecom + sell-through documents
  - BlobSink     (Phase 2) writes wholesale PO/shipment CSV files

A CompositeSink fans a single write out to the appropriate backend per source.
The methods below are the full surface; LocalSink implements all of them, the
cloud sinks implement the subset they own.
"""
from __future__ import annotations

from datetime import date
from typing import Protocol


class Sink(Protocol):
    # Source 1 — boutiques (relational rows)
    def write_pos(self, d: date, rows: list[dict]) -> None: ...
    def write_clients(self, d: date, rows: list[dict]) -> None: ...
    def write_inventory(self, d: date, rows: list[dict]) -> None: ...
    def write_after_sales(self, d: date, rows: list[dict]) -> None: ...
    def write_masters(self, masters: dict[str, list[dict]]) -> None: ...

    # Source 2 — online store (nested JSON documents)
    def write_ecom_orders(self, d: date, docs: list[dict]) -> None: ...
    def write_ecom_events(self, d: date, docs: list[dict]) -> None: ...
    def write_ecom_returns(self, d: date, docs: list[dict]) -> None: ...

    # Source 3 — wholesale (files + portal docs)
    def write_wholesale_file(self, partner_id: str, kind: str, filename: str, content: str) -> None: ...
    def write_sellthrough(self, partner_id: str, d: date, doc: dict) -> None: ...

    def close(self) -> None: ...
