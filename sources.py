"""
Stubbed data sources.

In production these would be real HTTP calls (warehouse management system API,
marketplace seller API). Here they're just JSON files on disk, but the
interface (get_stock / write_stock) is exactly what you'd implement against
a real API, so swapping the stub for the real thing later is a drop-in change.
"""
import json
import os
from dataclasses import dataclass
from typing import Optional


class SourceUnavailableError(Exception):
    """Raised when a source cannot be reached (timeout, 5xx, connection error, etc)."""
    pass


@dataclass
class StockReading:
    sku: str
    qty: int
    updated_at: str  # ISO8601
    available: bool
    source: str


class JsonStubSource:
    """Base class for a stubbed inventory source backed by a JSON file."""

    def __init__(self, path: str, name: str):
        self.path = path
        self.name = name
        self._force_down_skus = set()  # SKUs to simulate as unreachable

    def simulate_outage(self, sku: str):
        """Mark this source as unreachable for a given SKU (for demo purposes)."""
        self._force_down_skus.add(sku)

    def clear_outage(self, sku: str):
        self._force_down_skus.discard(sku)

    def _load(self) -> dict:
        with open(self.path, "r") as f:
            return json.load(f)

    def _save(self, data: dict):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def get_stock(self, sku: str) -> StockReading:
        if sku in self._force_down_skus:
            raise SourceUnavailableError(
                f"{self.name} did not respond for {sku} (simulated timeout)"
            )
        data = self._load()
        if sku not in data:
            raise KeyError(f"{sku} not found in {self.name}")
        row = data[sku]
        return StockReading(
            sku=sku,
            qty=row["qty"],
            updated_at=row["updated_at"],
            available=row["available"],
            source=self.name,
        )

    def write_stock(self, sku: str, qty: int, updated_at: str, available: bool = True):
        """Used when the agent corrects a source to match the chosen authoritative value."""
        data = self._load()
        data[sku] = {"qty": qty, "updated_at": updated_at, "available": available}
        self._save(data)

    def all_skus(self):
        return list(self._load().keys())


class WarehouseSource(JsonStubSource):
    def __init__(self, path: str = None):
        path = path or os.path.join(os.path.dirname(__file__), "data", "warehouse.json")
        super().__init__(path, name="warehouse")


class MarketplaceSource(JsonStubSource):
    def __init__(self, path: str = None):
        path = path or os.path.join(os.path.dirname(__file__), "data", "marketplace.json")
        super().__init__(path, name="marketplace")
