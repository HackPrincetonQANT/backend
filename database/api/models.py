from pydantic import BaseModel, Field
from typing import Optional


class TransactionInsert(BaseModel):
    id: str
    user_id: str
    transaction_id: str
    merchant: str
    amount_cents: int
    currency: str = Field(min_length=1, max_length=6)
    category: str
    need_or_want: str = Field(pattern="^(need|want)$")
    confidence: float = 1.0
    # ISO8601 string with timezone is ok; we cast in SQL
    occurred_at: str


class UserReply(BaseModel):
    id: str
    transaction_id: str
    user_id: str
    user_label: str = Field(pattern="^(need|want)$")
    received_at: str  # ISO8601