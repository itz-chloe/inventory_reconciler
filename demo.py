"""
Demo script for the video walkthrough.

Walks through the stub dataset, which is deliberately seeded with 5 SKUs
covering distinct situations, then simulates a live source outage and runs
a second pass to show the agent reacting to a *new* conflict it hasn't seen
before (not just replaying a fixed script).

Run: python demo.py
"""
from agent import build_agent

SCENARIO_NOTES = {
    "SKU-1001": "Values diverge by more than the minor-drift threshold, but "
                "marketplace's reading is clearly more recent -> RECENCY_TIEBREAK.",
    "SKU-1002": "Both sources agree -> IN_AGREEMENT, no action.",
    "SKU-1003": "Values diverge by 60 units, far past the large-divergence "
                "threshold -> LARGE_DIVERGENCE, flagged, not auto-corrected.",
    "SKU-1004": "Values diverge by only 1 unit -> MINOR_DRIFT, auto-corrected "
                "silently since the risk of being wrong is low.",
    "SKU-1005": "Warehouse says unavailable, marketplace still shows 5 units "
                "for sale -> AVAILABILITY_MISMATCH, flagged (revenue-impacting).",
}


def main():
    agent = build_agent()

    print("=" * 78)
    print("PASS 1: baseline reconciliation over seeded conflict scenarios")
    print("=" * 78)
    decisions = agent.reconcile_all()

    print("\n" + "=" * 78)
    print("Scenario-by-scenario explanation:")
    print("=" * 78)
    for d in decisions:
        note = SCENARIO_NOTES.get(d.sku, "")
        print(f"\n{d.sku}: {note}")
        print(f"  Rule applied : {d.rule}")
        print(f"  Action taken : {d.action}")

    print("\n" + "=" * 78)
    print("PASS 2: simulating a live warehouse outage on SKU-1002, then re-running")
    print("(this demonstrates the agent reacting to a NEW conflict type live,")
    print(" not just replaying the same fixed sequence)")
    print("=" * 78)
    agent.warehouse.simulate_outage("SKU-1002")
    d = agent.reconcile_sku("SKU-1002")
    print(f"\n  Rule applied : {d.rule}")
    print(f"  Action taken : {d.action}")
    agent.warehouse.clear_outage("SKU-1002")

    print("\nDone. Full structured log written to logs/decisions.jsonl")


if __name__ == "__main__":
    main()
