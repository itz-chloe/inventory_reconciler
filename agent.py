"""
InventoryReconciliationAgent

Multi-step agent loop, per SKU:
  1. Query warehouse source
  2. Query marketplace source
  3. Hand both readings (or errors) to the policy engine
  4. Execute the resulting action (write-back correction, or just flag)
  5. Log the decision with full reasoning (console + JSONL file)

Run modes:
  --once           run a single reconciliation pass over all SKUs and exit
  --interval N      run continuously, sleeping N seconds between passes
"""
import argparse
import json
import time
from datetime import datetime, timezone

from sources import WarehouseSource, MarketplaceSource, SourceUnavailableError
from policy import ReconciliationPolicy, Decision

LOG_PATH = "logs/decisions.jsonl"


class InventoryReconciliationAgent:
    def __init__(self, warehouse: WarehouseSource, marketplace: MarketplaceSource,
                 policy: ReconciliationPolicy, log_path: str = LOG_PATH):
        self.warehouse = warehouse
        self.marketplace = marketplace
        self.policy = policy
        self.log_path = log_path

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def _log(self, decision: Decision):
        record = {
            "timestamp": self._now(),
            "sku": decision.sku,
            "rule": decision.rule,
            "chosen_source": decision.chosen_source,
            "action": decision.action,
            "reason": decision.reason,
            "warehouse_reading": decision.warehouse_reading,
            "marketplace_reading": decision.marketplace_reading,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        # Human-readable console output -- this is what you'd screen-record for the demo video
        print(f"\n[{record['timestamp']}] SKU={decision.sku}  RULE={decision.rule}  ACTION={decision.action}")
        print(f"  -> {decision.reason}")

    def _execute(self, decision: Decision):
        """Apply the action decided by the policy: write corrections back to a source."""
        if decision.action == "auto_correct_marketplace":
            self.marketplace.write_stock(
                decision.sku,
                qty=decision.warehouse_reading["qty"],
                updated_at=self._now(),
                available=decision.warehouse_reading["available"],
            )
            print(f"  -> WROTE marketplace.{decision.sku} = {decision.warehouse_reading['qty']}")
        elif decision.action == "auto_correct_warehouse":
            self.warehouse.write_stock(
                decision.sku,
                qty=decision.marketplace_reading["qty"],
                updated_at=self._now(),
                available=decision.marketplace_reading["available"],
            )
            print(f"  -> WROTE warehouse.{decision.sku} = {decision.marketplace_reading['qty']}")
        elif decision.action == "flag_for_review":
            print(f"  -> FLAGGED {decision.sku} for manual review (no write-back)")
        elif decision.action == "await_source_recovery":
            print(f"  -> WAITING on downed source to recover for {decision.sku} (no write-back)")
        # "no_action" -> nothing to do

    def reconcile_sku(self, sku: str) -> Decision:
        w_reading, w_error = None, None
        m_reading, m_error = None, None

        try:
            w_reading = self.warehouse.get_stock(sku)
        except SourceUnavailableError as e:
            w_error = str(e)

        try:
            m_reading = self.marketplace.get_stock(sku)
        except SourceUnavailableError as e:
            m_error = str(e)

        decision = self.policy.decide(sku, w_reading, w_error, m_reading, m_error)
        self._execute(decision)
        self._log(decision)
        return decision

    def reconcile_all(self):
        skus = sorted(set(self.warehouse.all_skus()) | set(self.marketplace.all_skus()))
        decisions = []
        for sku in skus:
            decisions.append(self.reconcile_sku(sku))
        return decisions

    def run_continuous(self, interval_seconds: int):
        print(f"Starting continuous reconciliation, interval={interval_seconds}s. Ctrl+C to stop.")
        try:
            while True:
                self.reconcile_all()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("Stopped.")


def build_agent() -> InventoryReconciliationAgent:
    return InventoryReconciliationAgent(
        warehouse=WarehouseSource(),
        marketplace=MarketplaceSource(),
        policy=ReconciliationPolicy(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inventory reconciliation agent")
    parser.add_argument("--once", action="store_true", help="Run a single pass and exit")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between passes in continuous mode")
    args = parser.parse_args()

    agent = build_agent()
    if args.once:
        agent.reconcile_all()
    else:
        agent.run_continuous(args.interval)
