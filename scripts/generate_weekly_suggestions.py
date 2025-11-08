#!/usr/bin/env python3
"""
Weekly Suggestions Job Script

Generates weekly alternative suggestions for all users with recent purchases.
Runs as a scheduled job (cron/scheduler) to populate weekly_suggestions_reports table.

Usage:
    python scripts/generate_weekly_suggestions.py [--week YYYY-MM-DD] [--user USER_ID] [--dry-run]

Arguments:
    --week: Specific week to process (default: last week)
    --user: Process only specific user (default: all users)
    --dry-run: Run without writing to database

Design Principles (CLAUDE.MD):
- Test-driven development
- Security-first (parameterized queries, logging)
- Graceful error handling
"""

import asyncio
import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'database', 'api'))

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', '.env')
load_dotenv(env_path)

# Dynamically load modules
def load_module(module_name: str, file_path: str):
    """Dynamically load a Python module"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load database helpers
db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'db.py')
db = load_module('db', db_path)

# Load suggestions helpers
suggestions_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'suggestions.py')
suggestions = load_module('suggestions', suggestions_path)

# Load weekly suggester
suggester_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester.py')
suggester = load_module('weekly_suggester', suggester_path)


def get_week_start_date(offset_weeks: int = -1) -> str:
    """
    Get the start date of a week (Monday).

    Args:
        offset_weeks: Number of weeks to offset (negative = past, 0 = current)

    Returns:
        ISO date string (YYYY-MM-DD) for Monday of the week
    """
    today = datetime.now()
    # Get Monday of current week
    days_since_monday = today.weekday()
    current_week_monday = today - timedelta(days=days_since_monday)

    # Apply offset
    target_week_monday = current_week_monday + timedelta(weeks=offset_weeks)

    return target_week_monday.strftime('%Y-%m-%d')


def get_users_with_purchases(week_start: str) -> List[str]:
    """
    Get list of users who made purchases in the specified week.

    Args:
        week_start: ISO week start date (YYYY-MM-DD)

    Returns:
        List of unique user IDs

    Security: Uses parameterized queries to prevent SQL injection
    """
    week_start_date = datetime.strptime(week_start, '%Y-%m-%d')
    week_end_date = week_start_date + timedelta(days=7)
    week_end = week_end_date.strftime('%Y-%m-%d')

    sql = """
        SELECT DISTINCT USER_ID
        FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.PURCHASE_ITEMS_TEST
        WHERE TS >= TO_TIMESTAMP_TZ(%s)
          AND TS < TO_TIMESTAMP_TZ(%s)
          AND USER_ID IS NOT NULL
        ORDER BY USER_ID
    """

    params = (week_start, week_end)
    rows = db.fetch_all(sql, params)

    return [row['USER_ID'] for row in rows]


async def process_user(
    user_id: str,
    week_start: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Generate and save weekly suggestions for a single user.

    Args:
        user_id: User identifier
        week_start: ISO week start date (YYYY-MM-DD)
        dry_run: If True, don't write to database

    Returns:
        Dict with processing results and metrics
    """
    start_time = datetime.now()

    try:
        # Generate suggestions using Dedalus + MCP
        print(f"  Generating suggestions for user {user_id}...")
        report = await suggester.generate_weekly_suggestions(user_id, week_start, top_n=5)

        # Save to database (unless dry-run)
        if not dry_run:
            print(f"  Saving report to database...")
            report_id = suggestions.upsert_weekly_report(user_id, week_start, report)
            report['report_id'] = report_id
        else:
            print(f"  [DRY-RUN] Would save report to database")
            report['report_id'] = 'dry-run-no-id'

        # Calculate processing time
        end_time = datetime.now()
        processing_seconds = (end_time - start_time).total_seconds()

        # Return metrics
        return {
            'user_id': user_id,
            'success': True,
            'items_analyzed': report.get('items_analyzed', 0),
            'items_with_alternatives': report.get('items_with_alternatives', 0),
            'total_savings': report.get('total_potential_savings', 0.0),
            'mcp_calls': report.get('mcp_calls_made', 0),
            'processing_seconds': round(processing_seconds, 2),
            'error': report.get('error')
        }

    except Exception as e:
        end_time = datetime.now()
        processing_seconds = (end_time - start_time).total_seconds()

        print(f"  ❌ Error processing user {user_id}: {str(e)}")

        return {
            'user_id': user_id,
            'success': False,
            'items_analyzed': 0,
            'items_with_alternatives': 0,
            'total_savings': 0.0,
            'mcp_calls': 0,
            'processing_seconds': round(processing_seconds, 2),
            'error': str(e)
        }


async def main(args):
    """
    Main job execution function.

    Processes all users (or specific user) for a given week.
    """
    print("="*70)
    print("WEEKLY SUGGESTIONS JOB")
    print("="*70)

    # Determine week to process
    if args.week:
        week_start = args.week
        print(f"Processing week: {week_start} (specified)")
    else:
        week_start = get_week_start_date(offset_weeks=-1)  # Last week
        print(f"Processing week: {week_start} (last week)")

    # Get users to process
    if args.user:
        users = [args.user]
        print(f"Processing user: {args.user} (specified)")
    else:
        print(f"\nQuerying users with purchases in week {week_start}...")
        users = get_users_with_purchases(week_start)
        print(f"Found {len(users)} users with purchases")

    if not users:
        print("\n✅ No users to process. Exiting.")
        return

    # Process each user
    print(f"\n{'='*70}")
    print(f"PROCESSING {len(users)} USER(S)")
    print(f"{'='*70}\n")

    results = []
    for i, user_id in enumerate(users, 1):
        print(f"[{i}/{len(users)}] Processing user: {user_id}")
        result = await process_user(user_id, week_start, dry_run=args.dry_run)
        results.append(result)

        # Log result
        if result['success']:
            print(f"  ✅ Success: {result['items_with_alternatives']} alternatives found, "
                  f"${result['total_savings']:.2f} potential savings, "
                  f"{result['mcp_calls']} MCP calls, "
                  f"{result['processing_seconds']}s")
        else:
            print(f"  ❌ Failed: {result['error']}")

        print()  # Blank line between users

    # Summary statistics
    print(f"{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    total_users = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total_users - successful

    total_items = sum(r['items_analyzed'] for r in results)
    total_alternatives = sum(r['items_with_alternatives'] for r in results)
    total_savings = sum(r['total_savings'] for r in results)
    total_mcp_calls = sum(r['mcp_calls'] for r in results)
    total_time = sum(r['processing_seconds'] for r in results)

    print(f"Users processed: {total_users}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"\nItems analyzed: {total_items}")
    print(f"Alternatives found: {total_alternatives}")
    print(f"Total potential savings: ${total_savings:.2f}")
    print(f"MCP calls made: {total_mcp_calls}")
    print(f"Total processing time: {total_time:.1f}s")

    if total_users > 0:
        print(f"Average per user: {total_time/total_users:.1f}s")

    if args.dry_run:
        print(f"\n⚠️  DRY-RUN MODE: No data was written to database")

    print(f"\n{'='*70}")

    # Write summary to log file
    if not args.dry_run:
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'weekly_suggestions_{timestamp}.json')

        log_data = {
            'week_start': week_start,
            'timestamp': timestamp,
            'dry_run': args.dry_run,
            'summary': {
                'total_users': total_users,
                'successful': successful,
                'failed': failed,
                'total_items': total_items,
                'total_alternatives': total_alternatives,
                'total_savings': total_savings,
                'total_mcp_calls': total_mcp_calls,
                'total_time_seconds': total_time
            },
            'results': results
        }

        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

        print(f"📝 Log saved to: {log_file}")

    print(f"\n✅ Job complete!\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate weekly alternative suggestions for all users'
    )
    parser.add_argument(
        '--week',
        type=str,
        help='Specific week to process (YYYY-MM-DD). Default: last week'
    )
    parser.add_argument(
        '--user',
        type=str,
        help='Process only specific user ID. Default: all users'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without writing to database'
    )

    args = parser.parse_args()

    # Run async main
    asyncio.run(main(args))
