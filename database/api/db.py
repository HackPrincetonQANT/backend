import os
from contextlib import contextmanager
from typing import Dict, Any, Iterable, List

from dotenv import load_dotenv
import snowflake.connector as sfc
from snowflake.connector import DictCursor
from pathlib import Path
from dotenv import load_dotenv

# Try a few likely locations without overwriting already-set env vars
for p in [
    Path(__file__).with_name(".env"),          # backend/database/api/.env
    Path(__file__).parents[2] / ".env",        # backend/.env
    Path.cwd() / ".env",                       # current working dir .env
]:
    load_dotenv(p, override=False)
# Load env from both places if present
load_dotenv("api/.env", override=False)
load_dotenv(".env", override=False)


def _conn_kwargs() -> Dict[str, str]:
    return dict(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


@contextmanager
def get_conn():
    conn = sfc.connect(**_conn_kwargs())
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(sql: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    with get_conn() as conn, conn.cursor(DictCursor) as cur:
        cur.execute(sql, params or {})
        return list(cur.fetchall())


def execute(sql: str, params: Dict[str, Any] | None = None) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        conn.commit()


def execute_many(sql: str, params_list: List[Dict[str, Any]]) -> int:
    """
    Execute a SQL statement with multiple parameter sets for batch operations.

    Expected input: SQL statement and list of parameter dictionaries
    Expected output: Number of rows affected
    """
    if not params_list:
        return 0

    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(sql, params_list)
        conn.commit()
        return cur.rowcount