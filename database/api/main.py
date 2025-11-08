# database/api/main.py

from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from . import queries as Q
from .db import fetch_all, execute
from .models import TransactionInsert, UserReply
from .semantic import search_similar_items
from .predictor import predict_next_purchases
from .do_llm import call_do_llm
from .suggestions import get_weekly_report, get_recent_reports

app = FastAPI(title="BalanceIQ Core API", version="0.1.0")


# ----------------------------------------------------------------------
# Basic health / core endpoints
# ----------------------------------------------------------------------


@app.get("/health")
def health():
    """
    Simple health check: returns current Snowflake user/role/db/schema.
    """
    try:
        rows = fetch_all(Q.SQL_HEALTH)
        return rows[0] if rows else JSONResponse({"ok": False}, status_code=500)
    except Exception as e:
        print("Health error:", repr(e))
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/feed")
def feed(user_id: str, limit: int = Query(20, ge=1, le=100)):
    """
    Recent transactions feed for a given user (from TRANSACTIONS table).
    """
    return fetch_all(Q.SQL_FEED, {"user_id": user_id, "limit": limit})


@app.get("/stats/category")
def stats_by_category(user_id: str, days: int = Query(30, ge=1, le=365)):
    """
    Category-level stats (counts, want/need rate, totals) over a window.
    """
    return fetch_all(Q.SQL_STATS_BY_CATEGORY, {"user_id": user_id, "days": days})


@app.get("/predictions")
def predictions(user_id: str):
    """
    Returns precomputed prediction rows (if any) from PREDICTIONS table.
    """
    return fetch_all(Q.SQL_PREDICTIONS, {"user_id": user_id})


@app.post("/transactions")
def upsert_transaction(txn: TransactionInsert):
    """
    Upsert a single transaction into TRANSACTIONS via MERGE.
    """
    execute(Q.SQL_MERGE_TXN, txn.model_dump())
    return {"status": "ok", "id": txn.id}


@app.post("/reply")
def upsert_reply(rep: UserReply):
    """
    Upsert a user's reply (need/want label) tied to a transaction.
    """
    execute(Q.SQL_MERGE_REPLY, rep.model_dump())
    return {"status": "ok", "id": rep.id}


# ----------------------------------------------------------------------
# Semantic search (vector-ish search over ITEM_TEXT)
# ----------------------------------------------------------------------


@app.get("/semantic-search")
def semantic_search(
    q: str = Query(..., description="Search text"),
    user_id: str = Query(...),
    limit: int = Query(5, ge=1, le=50),
):
    """
    Semantic search over a user's transactions using Snowflake embeddings
    and a Python-side cosine similarity.
    """
    return search_similar_items(q, user_id, limit)


# ----------------------------------------------------------------------
# App-facing endpoints for the frontend / mobile
# ----------------------------------------------------------------------


@app.get("/api/user/{user_id}/transactions")
def get_user_transactions(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """
    Return recent transactions for a user in a simplified shape
    for the frontend/mobile app, based on PURCHASE_ITEMS_TEST.

    Shape:
    [
      {
        "id": "t123",
        "item": "Starbucks · Coffee",
        "amount": 5.25,
        "date": "<ISO timestamp>",
        "category": "Coffee"
      },
      ...
    ]
    """

    # NOTE: This uses PURCHASE_ITEMS_TEST, not TRANSACTIONS.
    sql = f"""
        SELECT
          ITEM_ID AS ID,
          COALESCE(ITEM_NAME, MERCHANT) AS ITEM_TEXT,
          (PRICE * 100)::NUMBER(12,0) AS AMOUNT_CENTS,
          TS AS OCCURRED_AT,
          CATEGORY
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.PURCHASE_ITEMS_TEST
        WHERE USER_ID = %s
        ORDER BY TS DESC
        LIMIT {limit}
    """

    rows = fetch_all(sql, (user_id,))

    out: List[Dict[str, Any]] = []
    for r in rows:
        cents = r.get("AMOUNT_CENTS")
        amount = float(cents) / 100.0 if cents is not None else None

        out.append(
            {
                "id": r["ID"],
                "item": r["ITEM_TEXT"],
                "amount": amount,
                "date": r["OCCURRED_AT"],  # FastAPI → ISO8601 in JSON
                "category": r["CATEGORY"],
            }
        )

    return out


# ----------------------------------------------------------------------
# Behavioral prediction (when will they buy next?)
# ----------------------------------------------------------------------


@app.get("/api/predict")
def api_predict(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(5, ge=1, le=20, description="Max number of predictions"),
) -> List[Dict[str, Any]]:
    """
    Behavioral prediction endpoint (uses PURCHASE_ITEMS_TEST).

    Uses predictor.predict_next_purchases() which:
      - Groups by (item_name, category)
      - Looks at historical TS times
      - Estimates an average interval between purchases
      - Predicts next_time = last_time + avg_interval
      - Computes a confidence score
    """
    try:
        return predict_next_purchases(user_id=user_id, limit=limit)
    except Exception as e:
        print("Prediction error:", repr(e))
        raise HTTPException(status_code=500, detail="Prediction failed")


# ----------------------------------------------------------------------
# AI Coach using DigitalOcean LLM
# ----------------------------------------------------------------------


@app.get("/api/coach")
def api_coach(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(3, ge=1, le=10, description="Max number of predicted items to consider"),
) -> Dict[str, Any]:
    """
    AI coach endpoint.

    - Uses predict_next_purchases() to get upcoming purchases.
    - Uses recent transactions (from PURCHASE_ITEMS_TEST).
    - Calls DigitalOcean LLM to generate a short, friendly coaching message.
    """
    # 1) Get predictions (re-use your predictor)
    try:
        predictions = predict_next_purchases(user_id=user_id, limit=limit)
    except Exception as e:
        print("Coach: prediction error", repr(e))
        predictions = []

    # 2) Get recent transactions (same source as /api/user/{user_id}/transactions)
    tx_sql = """
        SELECT
          ITEM_ID AS ID,
          COALESCE(ITEM_NAME, MERCHANT) AS ITEM_TEXT,
          (PRICE * 100)::NUMBER(12,0) AS AMOUNT_CENTS,
          TS AS OCCURRED_AT,
          CATEGORY
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.PURCHASE_ITEMS_TEST
        WHERE USER_ID = %s
        ORDER BY TS DESC
        LIMIT 20
    """
    try:
        tx_rows = fetch_all(tx_sql, (user_id,))
    except Exception as e:
        print("Coach: transactions error", repr(e))
        tx_rows = []

    # 3) Summarize transactions for the LLM (compact JSON-ish summary)
    summarized_txs: List[Dict[str, Any]] = []
    for r in tx_rows:
        cents = r.get("AMOUNT_CENTS")
        amount = float(cents) / 100.0 if cents is not None else None
        ts = r.get("OCCURRED_AT")
        summarized_txs.append(
            {
                "item": r.get("ITEM_TEXT"),
                "amount": amount,
                "category": r.get("CATEGORY"),
                "timestamp": ts.isoformat() if ts else None,
            }
        )

    import json

    coach_system_prompt = (
        "You are a friendly financial coach for a budgeting app with a cute mascot. "
        "The mascot gets happier when the user saves money or stays on track, and sadder when "
        "they overspend. You must be supportive, non-judgmental, and very concise."
    )

    user_prompt = (
        "Here is this user's recent spending history and predicted upcoming purchases.\n\n"
        f"Recent transactions (JSON):\n{json.dumps(summarized_txs, default=str)[:4000]}\n\n"
        f"Predicted upcoming purchases (JSON):\n{json.dumps(predictions, default=str)[:4000]}\n\n"
        "1. Briefly summarize their spending patterns.\n"
        "2. Suggest ONE or TWO concrete, realistic actions to save money in the next week.\n"
        "3. Mention how the mascot will feel (happier/sadder) if they follow or ignore the advice.\n"
        "Answer in 3 short sentences max."
    )

    # 4) Call DigitalOcean LLM
    try:
        coach_text = call_do_llm(
            system_prompt=coach_system_prompt,
            user_prompt=user_prompt,
        )
    except Exception as e:
        print("Coach: LLM error", repr(e))
        raise HTTPException(status_code=500, detail="Coach LLM failed")

    # 5) Return both the message and the raw data driving it
    return {
        "message": coach_text,
        "predictions": predictions,
        "recent_transactions": summarized_txs,
    }


# ----------------------------------------------------------------------
# Weekly Alternative Suggestions
# ----------------------------------------------------------------------


@app.get("/api/user/{user_id}/weekly_alternatives")
def api_weekly_alternatives(
    user_id: str,
    week: str = Query(None, description="ISO week start date (YYYY-MM-DD). If not provided, returns most recent report."),
) -> Dict[str, Any]:
    """
    Get weekly alternative suggestions for a user.

    Returns cached weekly suggestion reports that show cheaper alternatives
    for the user's purchases across major retailers.

    Query Parameters:
        - week: Optional ISO week start date (YYYY-MM-DD)
          If not provided, returns the most recent report

    Returns:
        {
            "user_id": "test_user_001",
            "week_start": "2024-01-22",
            "week_end": "2024-01-29",
            "findings": [
                {
                    "item_name": "Ring Video Doorbell 3",
                    "original_price": 119.99,
                    "original_merchant": "Amazon",
                    "alternative_merchant": "Best Buy",
                    "total_landed_cost": 106.99,
                    "total_savings": 13.00,
                    "url": "https://www.bestbuy.com/...",
                    ...
                }
            ],
            "total_potential_savings": 42.50,
            "items_analyzed": 5,
            "items_with_alternatives": 3,
            "created_at": "2024-01-27T10:30:00Z",
            "updated_at": "2024-01-27T10:30:00Z"
        }

    Performance: <800ms (served from cached reports in Snowflake)
    """
    if week:
        # Get specific week's report
        report = get_weekly_report(user_id, week)

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"No weekly alternatives report found for user {user_id} and week {week}"
            )

        return report

    else:
        # Get most recent report
        recent_reports = get_recent_reports(user_id, limit=1)

        if not recent_reports:
            raise HTTPException(
                status_code=404,
                detail=f"No weekly alternatives reports found for user {user_id}"
            )

        return recent_reports[0]


@app.get("/api/user/{user_id}/weekly_alternatives/history")
def api_weekly_alternatives_history(
    user_id: str,
    limit: int = Query(4, ge=1, le=12, description="Number of recent reports to return"),
) -> List[Dict[str, Any]]:
    """
    Get recent weekly alternative suggestions history for a user.

    Returns up to `limit` recent reports, ordered by week_start descending.
    Default is 4 reports (approximately 1 month of history).

    Returns:
        [
            {
                "user_id": "test_user_001",
                "week_start": "2024-01-22",
                "week_end": "2024-01-29",
                "total_potential_savings": 42.50,
                "items_analyzed": 5,
                "items_with_alternatives": 3,
                "findings": [...],
                ...
            },
            ...
        ]
    """
    reports = get_recent_reports(user_id, limit=limit)

    if not reports:
        # Return empty list instead of 404 for history endpoint
        return []

    return reports


@app.get("/api/user/{user_id}/weekly_alternatives/stream")
async def stream_weekly_alternatives(
    user_id: str,
    week: str = Query(None, description="ISO week start date (YYYY-MM-DD). If not provided, uses last week."),
):
    """
    Stream weekly alternative suggestions with real-time progress (Server-Sent Events).

    This endpoint provides live updates as the AI analyzes purchases and discovers
    cheaper alternatives. Perfect for showing progress in the UI.

    Query Parameters:
        - week: Optional ISO week start date (YYYY-MM-DD)
          If not provided, uses last week

    Returns:
        Server-Sent Events (text/event-stream) with progress updates:
        - start: Analysis beginning
        - items_loaded: Purchases fetched
        - analyzing: AI processing
        - found: Alternative discovered
        - complete: Analysis finished
        - error: Error occurred

    Example frontend usage:
        ```javascript
        const eventSource = new EventSource('/api/user/test_user_001/weekly_alternatives/stream');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data.event, data);
        };
        ```

    Performance: Real-time streaming (5-10 seconds total)
    """
    import importlib.util
    import os
    import json

    # Dynamically load streaming module
    stream_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'services', 'weekly_suggester_stream.py')
    spec = importlib.util.spec_from_file_location("weekly_suggester_stream", stream_path)
    stream_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stream_module)

    # Determine week to process
    if not week:
        from datetime import datetime, timedelta
        # Default to last week
        today = datetime.now()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        week = last_monday.strftime('%Y-%m-%d')

    async def event_generator():
        """Generate SSE events from streaming suggester"""
        try:
            async for event_data in stream_module.generate_weekly_suggestions_stream(user_id, week):
                # Format as SSE: data: {json}\n\n
                yield f"data: {json.dumps(event_data)}\n\n"

        except Exception as e:
            # Send error event
            error_event = {
                "event": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

