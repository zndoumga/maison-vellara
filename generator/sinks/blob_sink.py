"""
BlobSink — uploads wholesale PO and shipment CSV files to Azure Blob Storage.

Blob layout mirrors the local output layout:
  wholesale/{partner_id}/po/{filename}
  wholesale/{partner_id}/shipments/{filename}

Files are overwritten on re-upload (same filename = same PO number = idempotent).
Sell-through goes to Firebase, not Blob.
"""
from __future__ import annotations

import os
from datetime import date

from azure.storage.blob import BlobServiceClient


def _client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    )


class BlobSink:
    def __init__(self):
        self.container = os.environ.get("AZURE_BLOB_CONTAINER", "wholesale")
        self._client = _client()
        self._container_client = self._client.get_container_client(self.container)

    def write_wholesale_file(self, partner_id: str, kind: str, filename: str, content: str) -> None:
        blob_name = f"wholesale/{partner_id}/{kind}/{filename}"
        blob_client = self._container_client.get_blob_client(blob_name)
        blob_client.upload_blob(content.encode("utf-8"), overwrite=True)

    # ---- Not handled by this sink ----------------------------------------
    def write_pos(self, d, rows): pass
    def write_clients(self, d, rows): pass
    def write_inventory(self, d, rows): pass
    def write_after_sales(self, d, rows): pass
    def write_masters(self, masters): pass
    def write_ecom_orders(self, d, docs): pass
    def write_ecom_events(self, d, docs): pass
    def write_ecom_returns(self, d, docs): pass
    def write_sellthrough(self, partner_id, d, doc): pass

    def close(self) -> None:
        self._client.close()
