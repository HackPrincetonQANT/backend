# database/api/predictor.py

from __future__ import annotations

from typing import List, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import math

from .db import fetch_all


def _compute_confidence(num_purchases: int, intervals_sec: List[float]) -> float:
    """
    Heuristic confidence score in [0, 1].

    Intuition:
    - More historical purchases → more confidence.
    - More regular intervals → more confidence.
    """

    if num_purchases < 2:
        return 0.0

    # Sample factor: saturates around 10 purchases
    sample_factor = min(num_purchases / 10.0, 1.0)  # 0..1

    # Regularity factor: how consistent the intervals are
    if not intervals_sec:
        regularity = 0.0
    else:
        mean = sum(intervals_sec) / len(intervals_sec)
        if mean <= 0:
            regularity = 0.0
        else:
            variance = sum((d - mean) ** 2 for d in intervals_sec) / len(intervals_sec)
            std = math.sqrt(variance)
            cv = std / mean  # coefficient of variation
            # cv ~ 0 → very regular, cv > 1 → very irregular
            regularity = max(0.0, min(1.0, 1.0 - cv))  # 1 - cv, clamped 0..1

    # Combine: base + weighted sample + weighted regularity
    base = 0.2
    confidence = base + 0.4 * sample_factor + 0.4 * regularity
    confidence = max(0.0, min(1.0, confidence))
    # Round just to keep JSON pretty
    return round(confidence, 3)


def predict_next_purchases(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Predict the next purchase times for a given user,
    based purely on PURCHASE_ITEMS_TEST.

    Logic:
      - Fetch all rows for the user (ITEM_NAME, CATEGORY, TS).
      - Group by (ITEM_NAME, CATEGORY).
      - For each group with at least 2 timestamps:
          * sort timestamps
          * compute intervals (seconds) between consecutive purchases
          * average interval → avg_interval_sec
          * next_time = last_ts + avg_interval_sec
          * confidence = _compute_confidence(num_purchases, intervals)
      - Sort predictions by soonest next_time and return top `limit`.
    """

    # 1) Pull history for this user from PURCHASE_ITEMS_TEST
    rows = fetch_all(
        """
        SELECT
          ITEM_NAME,
          CATEGORY,
          TS
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.PURCHASE_ITEMS_TEST
        WHERE USER_ID = %s
        ORDER BY TS ASC
        """,
        (user_id,),
    )

    if len(rows) < 2:
        # Not enough history to say anything meaningful
        return []

    # 2) Group timestamps by (item_name, category)
    series: Dict[Tuple[str, str], List[datetime]] = defaultdict(list)

    for r in rows:
        item_name = r.get("ITEM_NAME")
        category = r.get("CATEGORY")
        ts = r.get("TS")

        if item_name is None or ts is None:
            continue

        key = (item_name, category or "")
        series[key].append(ts)

    predictions: List[Dict[str, Any]] = []

    # 3) For each group with at least 2 purchases, compute prediction
    for (item_name, category), times in series.items():
        if len(times) < 2:
            continue

        times_sorted = sorted(times)

        # Intervals in seconds between consecutive purchases
        intervals_sec: List[float] = []
        for t1, t2 in zip(times_sorted, times_sorted[1:]):
            if t2 > t1:
                delta = (t2 - t1).total_seconds()
                if delta > 0:
                    intervals_sec.append(delta)

        if not intervals_sec:
            continue

        avg_interval_sec = sum(intervals_sec) / len(intervals_sec)
        last_time = times_sorted[-1]
        predicted_time = last_time + timedelta(seconds=avg_interval_sec)

        num_purchases = len(times_sorted)
        confidence = _compute_confidence(num_purchases, intervals_sec)

        predictions.append(
            {
                "item": item_name,
                "category": category,
                "next_time": predicted_time,
                "confidence": confidence,
                "samples": num_purchases,
            }
        )

    # 4) Sort by soonest predicted time & truncate
    predictions.sort(key=lambda p: p["next_time"])
    return predictions[:limit]
