"""
Reconciliation policy.

This module is the "brain" of the agent. It contains the decision rules,
written down explicitly so that anyone reading this file (or the logs it
produces) can audit why a given call was made, and change the rule if the
business logic should change.

RULES (evaluated in this order):

1. SOURCE_UNAVAILABLE
   If one source could not be reached at all, we cannot compare values, so we
   trust whichever source DID respond. We do NOT overwrite the down source
   automatically -- we flag it to be re-synced once it's back, because
   "unavailable" often means stale infra state, not necessarily wrong data.

2. AVAILABILITY_MISMATCH
   If the two sources disagree on whether the item is available at all
   (e.g. warehouse says out-of-stock/0, marketplace still shows units for
   sale), this is treated as high-risk regardless of quantity, because it
   directly affects whether customers can buy something that doesn't exist.
   We trust the warehouse's availability flag (it reflects physical reality)
   but we FLAG it for manual review rather than silently delisting, since an
   auto-delist has real revenue impact.

3. MINOR_DRIFT (values differ, but by <= SMALL_THRESHOLD units)
   Small differences are normal (in-flight orders, sync lag) and are auto-
   corrected: the warehouse count is trusted as the source of physical truth
   and the marketplace is updated to match. This is safe to automate because
   the blast radius of being wrong by a couple of units is low.

4. RECENCY_TIEBREAK (values differ by more than SMALL_THRESHOLD but
   <= LARGE_THRESHOLD)
   The gap is too big to auto-correct blindly, but not so big that it's
   obviously an error. We trust whichever source was updated more recently,
   on the theory that a more recent update likely reflects a real recent
   event (a sale, a restock) that the other source hasn't caught up to yet.
   If both were updated within RECENCY_WINDOW_SECONDS of each other (i.e.
   recency doesn't clearly separate them), we fall back to each source's
   historical accuracy score as the tiebreaker.

5. LARGE_DIVERGENCE (values differ by more than LARGE_THRESHOLD)
   Too large a gap to trust any automated rule -- could be a sync bug, a
   miscount, or a fraud/theft situation. Always flagged for manual review,
   no automatic correction is applied.

Every decision returns a Decision object with the rule name, the chosen
source (if any), the action taken, and a human-readable reason, so it can be
logged verbatim.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sources import StockReading

SMALL_THRESHOLD = 2          # units; drift at or below this is auto-corrected
LARGE_THRESHOLD = 20         # units; drift above this always gets flagged
RECENCY_WINDOW_SECONDS = 120  # timestamps within this window are "too close to call"


@dataclass
class Decision:
    sku: str
    rule: str
    chosen_source: Optional[str]   # "warehouse" | "marketplace" | None
    action: str                    # "auto_correct_marketplace" | "auto_correct_warehouse"
                                    # | "flag_for_review" | "no_action" | "await_source_recovery"
    reason: str
    warehouse_reading: Optional[dict] = None
    marketplace_reading: Optional[dict] = None


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class ReconciliationPolicy:
    def __init__(self, accuracy_scores: dict = None):
        # historical accuracy score per source, used only as a last-resort
        # tiebreaker in RECENCY_TIEBREAK when timestamps are ~equal.
        # In a real system this would be persisted and updated over time
        # based on which source's value was later confirmed correct by a
        # human resolving a flagged case.
        self.accuracy_scores = accuracy_scores or {"warehouse": 1.0, "marketplace": 1.0}

    def decide(
        self,
        sku: str,
        warehouse_reading: Optional[StockReading],
        warehouse_error: Optional[str],
        marketplace_reading: Optional[StockReading],
        marketplace_error: Optional[str],
    ) -> Decision:

        w = warehouse_reading
        m = marketplace_reading

        # --- Rule 1: SOURCE_UNAVAILABLE ---------------------------------
        if warehouse_error and not marketplace_error:
            return Decision(
                sku=sku, rule="SOURCE_UNAVAILABLE", chosen_source="marketplace",
                action="await_source_recovery",
                reason=(
                    f"Warehouse source unreachable ({warehouse_error}). Trusting "
                    f"marketplace value ({m.qty} units, updated {m.updated_at}) as "
                    f"the only available reading. Warehouse will be re-checked next "
                    f"cycle; no write-back performed since we can't confirm the "
                    f"warehouse's true state."
                ),
                marketplace_reading=m.__dict__,
            )
        if marketplace_error and not warehouse_error:
            return Decision(
                sku=sku, rule="SOURCE_UNAVAILABLE", chosen_source="warehouse",
                action="await_source_recovery",
                reason=(
                    f"Marketplace source unreachable ({marketplace_error}). Trusting "
                    f"warehouse value ({w.qty} units, updated {w.updated_at}) as the "
                    f"only available reading. Marketplace will be re-checked next "
                    f"cycle; no write-back performed since the marketplace feed "
                    f"could not confirm its current state."
                ),
                warehouse_reading=w.__dict__,
            )
        if warehouse_error and marketplace_error:
            return Decision(
                sku=sku, rule="SOURCE_UNAVAILABLE", chosen_source=None,
                action="flag_for_review",
                reason=(
                    f"Both sources unreachable (warehouse: {warehouse_error}; "
                    f"marketplace: {marketplace_error}). No data to reconcile -- "
                    f"flagging for manual investigation of the integration itself."
                ),
            )

        # --- Rule 2: AVAILABILITY_MISMATCH ------------------------------
        if w.available != m.available:
            return Decision(
                sku=sku, rule="AVAILABILITY_MISMATCH", chosen_source="warehouse",
                action="flag_for_review",
                reason=(
                    f"Availability flags disagree: warehouse says available="
                    f"{w.available}, marketplace says available={m.available}. "
                    f"Warehouse availability is treated as ground truth since it "
                    f"reflects physical stock, but this is flagged rather than "
                    f"auto-corrected because delisting/relisting has direct "
                    f"revenue impact and should be human-confirmed."
                ),
                warehouse_reading=w.__dict__, marketplace_reading=m.__dict__,
            )

        # --- Compute divergence -----------------------------------------
        diff = abs(w.qty - m.qty)

        # --- Rule 3: MINOR_DRIFT ------------------------------------------
        if diff <= SMALL_THRESHOLD:
            if diff == 0:
                return Decision(
                    sku=sku, rule="IN_AGREEMENT", chosen_source=None,
                    action="no_action",
                    reason=f"Both sources report {w.qty} units. No conflict, no action needed.",
                    warehouse_reading=w.__dict__, marketplace_reading=m.__dict__,
                )
            return Decision(
                sku=sku, rule="MINOR_DRIFT", chosen_source="warehouse",
                action="auto_correct_marketplace",
                reason=(
                    f"Values differ by {diff} unit(s) (warehouse={w.qty}, "
                    f"marketplace={m.qty}), within the auto-correct threshold of "
                    f"{SMALL_THRESHOLD}. Warehouse is trusted as the source of "
                    f"physical truth for small drift, so marketplace is updated "
                    f"to {w.qty} to match."
                ),
                warehouse_reading=w.__dict__, marketplace_reading=m.__dict__,
            )

        # --- Rule 5: LARGE_DIVERGENCE -------------------------------------
        if diff > LARGE_THRESHOLD:
            return Decision(
                sku=sku, rule="LARGE_DIVERGENCE", chosen_source=None,
                action="flag_for_review",
                reason=(
                    f"Values differ by {diff} units (warehouse={w.qty}, "
                    f"marketplace={m.qty}), exceeding the large-divergence "
                    f"threshold of {LARGE_THRESHOLD}. Gap is too large to trust "
                    f"an automated correction (possible miscount, sync bug, or "
                    f"shrinkage) -- flagging for manual investigation instead."
                ),
                warehouse_reading=w.__dict__, marketplace_reading=m.__dict__,
            )

        # --- Rule 4: RECENCY_TIEBREAK --------------------------------------
        w_time = _parse_ts(w.updated_at)
        m_time = _parse_ts(m.updated_at)
        gap_seconds = abs((w_time - m_time).total_seconds())

        if gap_seconds > RECENCY_WINDOW_SECONDS:
            newer = "warehouse" if w_time > m_time else "marketplace"
            newer_reading = w if newer == "warehouse" else m
            action = "auto_correct_marketplace" if newer == "warehouse" else "auto_correct_warehouse"
            return Decision(
                sku=sku, rule="RECENCY_TIEBREAK", chosen_source=newer,
                action=action,
                reason=(
                    f"Values differ by {diff} units (warehouse={w.qty} @ "
                    f"{w.updated_at}, marketplace={m.qty} @ {m.updated_at}) -- too "
                    f"large for auto minor-drift correction, too small to be an "
                    f"obvious data error. {newer.capitalize()}'s reading is "
                    f"{gap_seconds:.0f}s more recent, suggesting it reflects a "
                    f"real, more up-to-date event (sale/restock). Trusting "
                    f"{newer} and syncing the other source to {newer_reading.qty}."
                ),
                warehouse_reading=w.__dict__, marketplace_reading=m.__dict__,
            )
        else:
            # Timestamps too close together to trust recency -- fall back to
            # historical accuracy score.
            winner = max(self.accuracy_scores, key=self.accuracy_scores.get)
            winner_reading = w if winner == "warehouse" else m
            action = "auto_correct_marketplace" if winner == "warehouse" else "auto_correct_warehouse"
            return Decision(
                sku=sku, rule="ACCURACY_TIEBREAK", chosen_source=winner,
                action=action,
                reason=(
                    f"Values differ by {diff} units and both readings were "
                    f"updated within {RECENCY_WINDOW_SECONDS}s of each other "
                    f"({gap_seconds:.0f}s apart), so recency doesn't clearly "
                    f"separate them. Falling back to historical accuracy score "
                    f"({self.accuracy_scores}) -- {winner} has the higher score, "
                    f"so it's trusted and the other source is corrected to "
                    f"{winner_reading.qty}."
                ),
                warehouse_reading=w.__dict__, marketplace_reading=m.__dict__,
            )
