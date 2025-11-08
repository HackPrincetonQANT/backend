# api/main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Query
from .semantic import search_similar_items
from .db import fetch_all, execute
from .models import TransactionInsert, UserReply
from . import queries as Q  # <— RELATIVE import
from fastapi import FastAPI, HTTPException, Query
from .db import fetch_all
from typing import List, Dict

app = FastAPI(title="BalanceIQ Core API", version="0.1.0")

@app.get("/health")
def health():
    rows = fetch_all(Q.SQL_HEALTH)
    return rows[0] if rows else JSONResponse({"ok": False}, status_code=500)

@app.get("/feed")
def feed(user_id: str, limit: int = Query(20, ge=1, le=100)):
    return fetch_all(Q.SQL_FEED, {"user_id": user_id, "limit": limit})

@app.get("/stats/category")
def stats_by_category(user_id: str, days: int = Query(30, ge=1, le=365)):
    return fetch_all(Q.SQL_STATS_BY_CATEGORY, {"user_id": user_id, "days": days})

@app.get("/predictions")
def predictions(user_id: str):
    return fetch_all(Q.SQL_PREDICTIONS, {"user_id": user_id})

@app.post("/transactions")
def upsert_transaction(txn: TransactionInsert):
    execute(Q.SQL_MERGE_TXN, txn.model_dump())
    return {"status": "ok", "id": txn.id}

@app.post("/reply")
def upsert_reply(rep: UserReply):
    execute(Q.SQL_MERGE_REPLY, rep.model_dump())
    return {"status": "ok", "id": rep.id}

@app.get("/semantic-search")
def semantic_search(
    q: str = Query(..., description="Search text"),
    user_id: str = Query(...),
    limit: int = Query(5, ge=1, le=50),
):
    """
    Semantic search over a user's transactions using Snowflake embeddings.
    """
    return search_similar_items(q, user_id, limit)



@app.get("/api/user/{user_id}/transactions")
def get_user_transactions(
    user_id: str,
    limit: int = Query(20, ge=1, le=100)
) -> List[Dict]:
    """
    Return recent transactions for a user in a simplified shape
    for the frontend/mobile app.
    """
    # Clamp limit safely and build SQL
    sql = f"""
        SELECT
          ID,
          COALESCE(ITEM_TEXT, MERCHANT) AS ITEM_TEXT,
          AMOUNT_CENTS,
          OCCURRED_AT,
          CATEGORY
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.TRANSACTIONS
        WHERE USER_ID = %s
        ORDER BY OCCURRED_AT DESC
        LIMIT {limit}
    """

    rows = fetch_all(sql, (user_id,))

    # Shape into what the app expects
    out = []
    for r in rows:
        cents = r.get("AMOUNT_CENTS")
        amount = float(cents) / 100.0 if cents is not None else None

        out.append({
            "id": r["ID"],
            "item": r["ITEM_TEXT"],
            "amount": amount,
            "date": r["OCCURRED_AT"],   # FastAPI will turn this into ISO8601
            "category": r["CATEGORY"],
        })

    return out


@app.get("/api/predict")
def predict_purchases(
    user_id: str,
    top_k: int = Query(3, ge=1, le=10)
):
    """
    Very simple behavioral prediction model.

    For each merchant the user has bought from at least twice,
    we estimate the average time between purchases and predict
    the next one.
    """

    # 1) Get all past transactions for the user ordered by time
    rows = fetch_all("""
        SELECT
          ID,
          COALESCE(ITEM_TEXT, MERCHANT) AS ITEM_TEXT,
          MERCHANT,
          CATEGORY,
          OCCURRED_AT
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.TRANSACTIONS
        WHERE USER_ID = %s
        ORDER BY OCCURRED_AT ASC
    """, (user_id,))

    if len(rows) < 2:
        # Not enough history to say anything meaningful
        return []

    # 2) Group timestamps by merchant
    by_merchant = defaultdict(list)
    meta = {}  # merchant -> (category, last_item_text)

    for r in rows:
        m = r["MERCHANT"]
        ts = r["OCCURRED_AT"]
        by_merchant[m].append(ts)
        meta[m] = (r["CATEGORY"], r["ITEM_TEXT"])

    predictions = []

    # 3) For each merchant with at least 2 purchases, compute avg interval
    for merchant, times in by_merchant.items():
        if len(times) < 2:
            continue

        times = sorted(times)
        deltas = [
            (t2 - t1).total_seconds()
            for t1, t2 in zip(times, times[1:])
            if t2 > t1
        ]
        if not deltas:
            continue

        avg_sec = sum(deltas) / len(deltas)
        last_time = times[-1]
        predicted_time = last_time.timestamp() + avg_sec

        category, item_text = meta[merchant]

        # Simple confidence: more repeats -> higher confidence, cap at 1.0
        samples = len(times)
        confidence = min(1.0, 0.3 + 0.15 * samples)  # tune as you like

        predictions.append({
            "merchant": merchant,
            "item": item_text,
            "category": category,
            "predicted_time": datetime.fromtimestamp(predicted_time, tz=timezone.utc),
            "confidence": confidence,
            "samples": samples,
        })

    # 4) Sort by soonest predicted time & truncate
    predictions.sort(key=lambda p: p["predicted_time"])
    return predictions[:top_k]