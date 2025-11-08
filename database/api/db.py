import os
from contextlib import contextmanager
from typing import Dict, Any, Iterable, List

from dotenv import load_dotenv
import snowflake.connector as sfc
from snowflake.connector import DictCursor

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