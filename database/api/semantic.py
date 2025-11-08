# backend/database/api/semantic.py

import math
import snowflake.connector as sfc
from db import get_conn  # reuse your existing connection helper


def cosine(a, b):
    """Compute cosine similarity between two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def search_similar_items(query: str, user_id: str, limit: int = 5):
    """
    Semantic search over TRANSACTIONS for a given user.

    1. Embed the query text using Cortex.
    2. Fetch recent transactions with ITEM_EMBED.
    3. Compute cosine similarity in Python.
    4. Return top-k most similar.
    """
    with get_conn() as conn, conn.cursor(sfc.DictCursor) as cur:
        # 1) Embed the query using Cortex
        cur.execute(
            """
            SELECT SNOWFLAKE.CORTEX.AI_EMBED_768('e5-base-v2', %s) AS QV
            """,
            (query,),
        )
        row = cur.fetchone()
        query_vec = row["QV"]  # Snowflake VECTOR -> Python list

        # 2) Pull candidate rows (e.g. most recent 200 for that user)
        cur.execute(
            """
            SELECT
                ID,
                ITEM_TEXT,
                ITEM_EMBED
            FROM TRANSACTIONS
            WHERE USER_ID = %s
              AND ITEM_EMBED IS NOT NULL
            ORDER BY OCCURRED_AT DESC
            LIMIT 200
            """,
            (user_id,),
        )
        candidates = cur.fetchall()

    # 3) Compute similarity in Python
    scored = []
    for r in candidates:
        emb = r["ITEM_EMBED"]
        sim = cosine(query_vec, emb)
        scored.append(
            {
                "id": r["ID"],
                "item_text": r["ITEM_TEXT"],
                "similarity": sim,
            }
        )

    # 4) Sort by similarity (high -> low) and return top-k
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:limit]