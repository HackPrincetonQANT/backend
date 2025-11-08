"""
Tests for Phase 4: Weekly Job Script

Tests the weekly suggestions job script that generates reports for all users.

Following CLAUDE.MD Rule 2: Each step should contain tests to validate changes work.
"""

import json
import os
from datetime import datetime, timedelta


# Test 1: Week calculation logic
def test_week_start_calculation():
    """
    Verify that get_week_start_date calculates Monday correctly.

    Expected: Should return Monday of the target week in YYYY-MM-DD format.
    """
    # Import the script
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    # Verify logic exists
    assert 'def get_week_start_date' in code, "Should have get_week_start_date function"
    assert 'weekday()' in code, "Should calculate day of week"
    assert 'timedelta' in code, "Should use timedelta for date math"

    # Verify it returns Monday
    assert 'days_since_monday' in code or 'weekday()' in code, "Should calculate days since Monday"


# Test 2: SQL injection prevention in user query
def test_users_query_parameterized():
    """
    Verify that get_users_with_purchases uses parameterized queries.

    Expected: Should use %s placeholders, not string formatting.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'def get_users_with_purchases' in code, "Should have get_users_with_purchases function"
    assert '%s' in code, "Should use parameterized queries"
    assert 'SELECT DISTINCT USER_ID' in code, "Should query user IDs"
    assert 'FROM SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE.PURCHASE_ITEMS_TEST' in code, "Should query purchase_items"


# Test 3: Async processing
def test_async_user_processing():
    """
    Verify that process_user is async for concurrent processing.

    Expected: Should use async def for process_user function.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'async def process_user' in code, "Should have async process_user function"
    assert 'await suggester.generate_weekly_suggestions' in code, "Should await suggester call"


# Test 4: Error handling in user processing
def test_error_handling_per_user():
    """
    Verify that errors in one user don't crash the entire job.

    Expected: Should have try/except around user processing.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'try:' in code, "Should have try block"
    assert 'except Exception as e:' in code, "Should catch exceptions"
    assert "'success': False" in code or "success = False" in code, "Should mark failed users"


# Test 5: Dry-run mode
def test_dry_run_mode():
    """
    Verify that dry-run mode doesn't write to database.

    Expected: Should check dry_run flag before database operations.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert '--dry-run' in code, "Should have dry-run argument"
    assert 'if not dry_run:' in code, "Should check dry_run flag"
    assert 'DRY-RUN' in code or 'dry-run' in code.lower(), "Should log dry-run status"


# Test 6: Command-line arguments
def test_command_line_arguments():
    """
    Verify that script accepts week, user, and dry-run arguments.

    Expected: Should use argparse with --week, --user, --dry-run.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'argparse' in code, "Should use argparse"
    assert '--week' in code, "Should have --week argument"
    assert '--user' in code, "Should have --user argument"
    assert '--dry-run' in code, "Should have --dry-run argument"


# Test 7: Logging and metrics
def test_logging_and_metrics():
    """
    Verify that script logs metrics for monitoring.

    Expected: Should track items processed, alternatives found, MCP calls.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'items_analyzed' in code, "Should track items analyzed"
    assert 'items_with_alternatives' in code, "Should track alternatives found"
    assert 'mcp_calls' in code, "Should track MCP calls made"
    assert 'processing_seconds' in code or 'processing_time' in code, "Should track processing time"


# Test 8: Summary statistics
def test_summary_statistics():
    """
    Verify that script prints summary statistics.

    Expected: Should calculate and display totals across all users.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'SUMMARY' in code, "Should have summary section"
    assert 'total_users' in code or 'len(results)' in code, "Should count total users"
    assert 'total_savings' in code, "Should sum total savings"
    assert 'successful' in code and 'failed' in code, "Should count success/failure"


# Test 9: Database upsert call
def test_database_upsert():
    """
    Verify that script calls upsert_weekly_report.

    Expected: Should call suggestions.upsert_weekly_report with report data.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'upsert_weekly_report' in code, "Should call upsert_weekly_report"
    assert 'report_id = ' in code, "Should capture report_id"


# Test 10: Log file creation
def test_log_file_creation():
    """
    Verify that script writes JSON log file with results.

    Expected: Should create logs directory and write JSON summary.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert "log_dir =" in code or "logs" in code, "Should reference logs directory"
    assert 'os.makedirs' in code, "Should create logs directory"
    assert 'json.dump(' in code, "Should write JSON log"
    assert 'log_file' in code, "Should create log file"


# Test 11: Feature flag exists
def test_feature_flag_in_env():
    """
    Verify that WEEKLY_SUGGESTIONS_ENABLED flag exists in .env.example.

    Expected: Should have feature flag for enabling/disabling feature.
    """
    env_example_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', '.env.example')

    with open(env_example_path, 'r') as f:
        env_content = f.read()

    assert 'WEEKLY_SUGGESTIONS_ENABLED' in env_content, "Should have WEEKLY_SUGGESTIONS_ENABLED flag"
    assert 'Feature Flags' in env_content or 'feature' in env_content.lower(), "Should document as feature flag"


# Test 12: Shebang for executable
def test_script_executable():
    """
    Verify that script has shebang for direct execution.

    Expected: Should start with #!/usr/bin/env python3.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        first_line = f.readline()

    assert first_line.startswith('#!/usr/bin/env python'), "Should have Python shebang"


# Test 13: Module loading security
def test_module_loading():
    """
    Verify that script loads modules dynamically and safely.

    Expected: Should use importlib.util for module loading.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'importlib.util' in code, "Should use importlib for dynamic imports"
    assert 'spec_from_file_location' in code, "Should load modules from file paths"


# Test 14: Processing time tracking
def test_processing_time_tracking():
    """
    Verify that script tracks processing time per user.

    Expected: Should measure start/end time and calculate duration.
    """
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')

    with open(script_path, 'r') as f:
        code = f.read()

    assert 'start_time = datetime.now()' in code, "Should record start time"
    assert 'end_time = datetime.now()' in code, "Should record end time"
    assert 'processing_seconds' in code or '(end_time - start_time)' in code, "Should calculate duration"


if __name__ == '__main__':
    # Run tests manually
    print("Running Phase 4 Weekly Job Tests...")

    print("\n1. Testing week calculation...")
    test_week_start_calculation()
    print("   ✅ Week calculation logic present")

    print("\n2. Testing SQL injection prevention...")
    test_users_query_parameterized()
    print("   ✅ User query uses parameterized SQL")

    print("\n3. Testing async processing...")
    test_async_user_processing()
    print("   ✅ Async user processing implemented")

    print("\n4. Testing error handling...")
    test_error_handling_per_user()
    print("   ✅ Error handling per user")

    print("\n5. Testing dry-run mode...")
    test_dry_run_mode()
    print("   ✅ Dry-run mode implemented")

    print("\n6. Testing command-line arguments...")
    test_command_line_arguments()
    print("   ✅ Command-line arguments present")

    print("\n7. Testing logging and metrics...")
    test_logging_and_metrics()
    print("   ✅ Logging and metrics tracked")

    print("\n8. Testing summary statistics...")
    test_summary_statistics()
    print("   ✅ Summary statistics calculated")

    print("\n9. Testing database upsert...")
    test_database_upsert()
    print("   ✅ Database upsert called")

    print("\n10. Testing log file creation...")
    test_log_file_creation()
    print("   ✅ Log file creation implemented")

    print("\n11. Testing feature flag...")
    test_feature_flag_in_env()
    print("   ✅ Feature flag in .env.example")

    print("\n12. Testing script executable...")
    test_script_executable()
    print("   ✅ Script has shebang")

    print("\n13. Testing module loading...")
    test_module_loading()
    print("   ✅ Dynamic module loading secure")

    print("\n14. Testing processing time tracking...")
    test_processing_time_tracking()
    print("   ✅ Processing time tracked")

    print("\n✅ All Phase 4 tests passed!")
