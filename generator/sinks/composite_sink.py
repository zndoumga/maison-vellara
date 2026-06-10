"""
CompositeSink — routes each write to the correct backend sink.

  Supabase  ← boutique data (POS, CRM, inventory, after-sales, masters)
  Firebase  ← online store (orders, events, returns) + sell-through docs
  Blob      ← wholesale files (PO, shipments)
"""
from __future__ import annotations

from datetime import date

from sinks.supabase_sink import SupabaseSink
from sinks.firebase_sink import FirebaseSink
from sinks.blob_sink import BlobSink


class CompositeSink:
    def __init__(self):
        self.supabase = SupabaseSink()
        self.firebase = FirebaseSink()
        self.blob = BlobSink()

    def write_masters(self, masters):
        self.supabase.write_masters(masters)

    def write_pos(self, d: date, rows):
        self.supabase.write_pos(d, rows)

    def write_clients(self, d: date, rows):
        self.supabase.write_clients(d, rows)

    def write_inventory(self, d: date, rows):
        self.supabase.write_inventory(d, rows)

    def write_after_sales(self, d: date, rows):
        self.supabase.write_after_sales(d, rows)

    def write_ecom_orders(self, d: date, docs):
        self.firebase.write_ecom_orders(d, docs)

    def write_ecom_events(self, d: date, docs):
        self.firebase.write_ecom_events(d, docs)

    def write_ecom_returns(self, d: date, docs):
        self.firebase.write_ecom_returns(d, docs)

    def write_wholesale_file(self, partner_id, kind, filename, content):
        self.blob.write_wholesale_file(partner_id, kind, filename, content)

    def write_sellthrough(self, partner_id, d: date, doc):
        self.firebase.write_sellthrough(partner_id, d, doc)

    def close(self):
        self.supabase.close()
        self.firebase.close()
        self.blob.close()
