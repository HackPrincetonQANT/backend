# database/api/semantic.py

from typing import List, Dict, Any
from .db import fetch_all


def search_similar_items(
    query: str,
    user_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Simple text-based semantic-ish search.

    For now, this does a case-insensitive ILIKE match on ITEM_NAME / MERCHANT
    in PURCHASE_ITEMS_TEST. This keeps the endpoint working without relying
    on Snowflake VECTOR features, which have been tricky.

    It returns rows shaped similarly to /api/user/{user_id}/transactions.
    """

    sql = """
        SELECT
          ITEM_ID AS ID,
          COALESCE(ITEM_NAME, MERCHANT) AS ITEM_TEXT,
          (PRICE * 100)::NUMBER(12,0) AS AMOUNT_CENTS,
          TS AS OCCURRED_AT,
          CATEGORY
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.PURCHASE_ITEMS_TEST
        WHERE USER_ID = %s
          AND (
            ITEM_NAME ILIKE %s
            OR MERCHANT ILIKE %s
            OR CATEGORY ILIKE %s
          )
        ORDER BY TS DESC
        LIMIT %s
    """

    like = f"%{query}%"
    params = (user_id, like, like, like, limit)
    rows = fetch_all(sql, params)

    out: List[Dict[str, Any]] = []
    for r in rows:
        cents = r.get("AMOUNT_CENTS")
        amount = float(cents) / 100.0 if cents is not None else None
        out.append(
            {
                "id": r["ID"],
                "item": r["ITEM_TEXT"],
                "amount": amount,
                "date": r["OCCURRED_AT"],
                "category": r["CATEGORY"],
            }
        )

    return out
