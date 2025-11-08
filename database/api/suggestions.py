# database/api/suggestions.py

"""
Database helpers for weekly alternative suggestions reports.

Provides functions to upsert and retrieve weekly suggestion reports
from the weekly_suggestions_reports table.

Security: Uses parameterized queries to prevent SQL injection.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from .db import fetch_all, execute
import json
import uuid


def upsert_weekly_report(
    user_id: str,
    week_start: str,
    report_data: Dict[str, Any]
) -> str:
    """
    Upsert a weekly suggestions report to Snowflake (idempotent).

    Uses MERGE to ensure only one report per (user_id, week_start) exists.
    If report already exists, updates it with new data.

    Args:
        user_id: User identifier
        week_start: ISO week start date (YYYY-MM-DD)
        report_data: Full report dict from generate_weekly_suggestions()

    Returns:
        report_id: UUID of the upserted report

    Security: Uses parameterized queries to prevent SQL injection
    """
    # Generate or use existing report_id
    report_id = str(uuid.uuid4())

    # Extract metadata from report
    week_end = report_data.get('week_end', week_start)
    total_savings = report_data.get('total_potential_savings', 0.0)
    items_analyzed = report_data.get('items_analyzed', 0)
    items_with_alternatives = report_data.get('items_with_alternatives', 0)
    mcp_calls_made = report_data.get('mcp_calls_made', 0)
    processing_time_ms = report_data.get('processing_time_ms', 0)

    # Extract location from report (city/state/country only, no lat/lon)
    # For privacy, we don't store exact coordinates in the reports table
    location_city = None
    location_state = None
    location_country = None

    # Serialize full report as JSON
    report_json = json.dumps(report_data)

    # MERGE statement for idempotent upsert
    sql = """
        MERGE INTO SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.weekly_suggestions_reports AS target
        USING (
            SELECT
                %s AS report_id,
                %s AS user_id,
                TO_DATE(%s) AS week_start,
                TO_DATE(%s) AS week_end,
                %s AS location_city,
                %s AS location_state,
                %s AS location_country,
                %s AS total_items,
                %s AS items_with_alts,
                %s AS total_savings_usd,
                PARSE_JSON(%s) AS report_json,
                %s AS mcp_calls_made,
                %s AS processing_time_ms,
                CURRENT_TIMESTAMP() AS created_at,
                CURRENT_TIMESTAMP() AS updated_at
        ) AS source
        ON target.user_id = source.user_id
           AND target.week_start = source.week_start
        WHEN MATCHED THEN UPDATE SET
            target.report_id = source.report_id,
            target.week_end = source.week_end,
            target.location_city = source.location_city,
            target.location_state = source.location_state,
            target.location_country = source.location_country,
            target.total_items = source.total_items,
            target.items_with_alts = source.items_with_alts,
            target.total_savings_usd = source.total_savings_usd,
            target.report_json = source.report_json,
            target.mcp_calls_made = source.mcp_calls_made,
            target.processing_time_ms = source.processing_time_ms,
            target.updated_at = source.updated_at
        WHEN NOT MATCHED THEN INSERT (
            report_id, user_id, week_start, week_end,
            location_city, location_state, location_country,
            total_items, items_with_alts, total_savings_usd,
            report_json, mcp_calls_made, processing_time_ms,
            created_at, updated_at
        ) VALUES (
            source.report_id, source.user_id, source.week_start, source.week_end,
            source.location_city, source.location_state, source.location_country,
            source.total_items, source.items_with_alts, source.total_savings_usd,
            source.report_json, source.mcp_calls_made, source.processing_time_ms,
            source.created_at, source.updated_at
        )
    """

    params = (
        report_id,
        user_id,
        week_start,
        week_end,
        location_city,
        location_state,
        location_country,
        items_analyzed,
        items_with_alternatives,
        total_savings,
        report_json,
        mcp_calls_made,
        processing_time_ms
    )

    execute(sql, params)
    return report_id


def get_weekly_report(
    user_id: str,
    week_start: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a weekly suggestions report from Snowflake.

    Args:
        user_id: User identifier
        week_start: ISO week start date (YYYY-MM-DD)

    Returns:
        Report dict if found, None otherwise

    Security: Uses parameterized queries to prevent SQL injection
    """
    sql = """
        SELECT
            report_id,
            user_id,
            week_start,
            week_end,
            location_city,
            location_state,
            location_country,
            total_items,
            items_with_alts,
            total_savings_usd,
            report_json,
            mcp_calls_made,
            processing_time_ms,
            created_at,
            updated_at
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.weekly_suggestions_reports
        WHERE user_id = %s
          AND week_start = TO_DATE(%s)
    """

    params = (user_id, week_start)
    rows = fetch_all(sql, params)

    if not rows:
        return None

    row = rows[0]

    # Parse the JSON report
    report_json = row.get('REPORT_JSON')
    if report_json:
        # Snowflake returns VARIANT as dict, not string
        if isinstance(report_json, str):
            report_data = json.loads(report_json)
        else:
            report_data = report_json
    else:
        report_data = {}

    # Enrich with metadata
    report_data['report_id'] = row.get('REPORT_ID')
    report_data['created_at'] = row.get('CREATED_AT')
    report_data['updated_at'] = row.get('UPDATED_AT')

    return report_data


def get_recent_reports(
    user_id: str,
    limit: int = 4
) -> list[Dict[str, Any]]:
    """
    Retrieve recent weekly suggestion reports for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of reports to return (default 4 = 1 month)

    Returns:
        List of report dicts, ordered by week_start descending

    Security: Uses parameterized queries to prevent SQL injection
    """
    sql = """
        SELECT
            report_id,
            user_id,
            week_start,
            week_end,
            total_items,
            items_with_alts,
            total_savings_usd,
            report_json,
            mcp_calls_made,
            processing_time_ms,
            created_at,
            updated_at
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.weekly_suggestions_reports
        WHERE user_id = %s
        ORDER BY week_start DESC
        LIMIT %s
    """

    params = (user_id, limit)
    rows = fetch_all(sql, params)

    reports = []
    for row in rows:
        # Parse the JSON report
        report_json = row.get('REPORT_JSON')
        if report_json:
            if isinstance(report_json, str):
                report_data = json.loads(report_json)
            else:
                report_data = report_json
        else:
            report_data = {}

        # Enrich with metadata
        report_data['report_id'] = row.get('REPORT_ID')
        report_data['created_at'] = row.get('CREATED_AT')
        report_data['updated_at'] = row.get('UPDATED_AT')

        reports.append(report_data)

    return reports
