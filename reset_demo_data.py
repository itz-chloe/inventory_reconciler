"""
Restores data/warehouse.json and data/marketplace.json to their original
seed state, and clears the decision log. Run this before each demo/recording
take, since the agent writes real corrections back to the stub files.
"""
import json
import os

WAREHOUSE_SEED = {
    "SKU-1001": {"qty": 50, "updated_at": "2026-08-13T09:00:00Z", "available": True},
    "SKU-1002": {"qty": 12, "updated_at": "2026-08-13T09:05:00Z", "available": True},
    "SKU-1003": {"qty": 200, "updated_at": "2026-08-13T08:30:00Z", "available": True},
    "SKU-1004": {"qty": 8, "updated_at": "2026-08-13T09:10:00Z", "available": True},
    "SKU-1005": {"qty": 0, "updated_at": "2026-08-13T07:00:00Z", "available": False},
}

MARKETPLACE_SEED = {
    "SKU-1001": {"qty": 47, "updated_at": "2026-08-13T09:05:30Z", "available": True},
    "SKU-1002": {"qty": 12, "updated_at": "2026-08-13T06:00:00Z", "available": True},
    "SKU-1003": {"qty": 140, "updated_at": "2026-08-13T09:20:00Z", "available": True},
    "SKU-1004": {"qty": 7, "updated_at": "2026-08-13T09:09:00Z", "available": True},
    "SKU-1005": {"qty": 5, "updated_at": "2026-08-13T09:15:00Z", "available": True},
}

HERE = os.path.dirname(__file__)

if __name__ == "__main__":
    with open(os.path.join(HERE, "data", "warehouse.json"), "w") as f:
        json.dump(WAREHOUSE_SEED, f, indent=2)
    with open(os.path.join(HERE, "data", "marketplace.json"), "w") as f:
        json.dump(MARKETPLACE_SEED, f, indent=2)
    os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
    open(os.path.join(HERE, "logs", "decisions.jsonl"), "w").close()
    print("Seed data restored, decision log cleared.")
