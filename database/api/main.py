# api/main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Query
from .semantic import search_similar_items
from .db import fetch_all, execute
from .models import TransactionInsert, UserReply
from . import queries as Q  # <— RELATIVE import

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