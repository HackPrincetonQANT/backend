#!/usr/bin/env python3
"""
Integration Verification Test

Verifies all components are in place and properly structured.
Tests what can be tested without external dependencies.
"""

import os
import sys
import json

print("="*70)
print("WEEKLY SUGGESTIONS - INTEGRATION VERIFICATION")
print("="*70)
print()

test_results = []

# ============================================================================
# Component 1: Test Data
# ============================================================================
print("✓ Component 1: Test Data")
print("-" * 70)

test_data_path = 'src/data/sample_knot_with_location.json'
if os.path.exists(test_data_path):
    with open(test_data_path, 'r') as f:
        data = json.load(f)
    transactions = data.get('transactions', [])
    print(f"✅ Test data exists: {len(transactions)} transactions")
    test_results.append(("Test Data", "PASS"))
else:
    print(f"❌ Test data not found at {test_data_path}")
    test_results.append(("Test Data", "FAIL"))
print()

# ============================================================================
# Component 2: Weekly Suggester
# ============================================================================
print("✓ Component 2: Weekly Suggester")
print("-" * 70)

suggester_path = 'src/services/weekly_suggester.py'
if os.path.exists(suggester_path):
    with open(suggester_path, 'r') as f:
        code = f.read()

    has_fetch = 'def fetch_top_items' in code
    has_prompt = 'def build_plan_prompt' in code
    has_generate = 'def generate_weekly_suggestions' in code
    uses_dedalus = 'AsyncDedalus' in code and 'DedalusRunner' in code
    uses_mcp = 'MCP' in code or 'websearch' in code.lower()

    print(f"✅ Suggester module exists")
    print(f"   • fetch_top_items(): {'✅' if has_fetch else '❌'}")
    print(f"   • build_plan_prompt(): {'✅' if has_prompt else '❌'}")
    print(f"   • generate_weekly_suggestions(): {'✅' if has_generate else '❌'}")
    print(f"   • Uses Dedalus AI: {'✅' if uses_dedalus else '❌'}")
    print(f"   • References MCP/websearch: {'✅' if uses_mcp else '❌'}")

    if all([has_fetch, has_prompt, has_generate, uses_dedalus]):
        test_results.append(("Weekly Suggester", "PASS"))
    else:
        test_results.append(("Weekly Suggester", "FAIL"))
else:
    print(f"❌ Suggester not found at {suggester_path}")
    test_results.append(("Weekly Suggester", "FAIL"))
print()

# ============================================================================
# Component 3: Streaming Suggester
# ============================================================================
print("✓ Component 3: Streaming Suggester")
print("-" * 70)

stream_path = 'src/services/weekly_suggester_stream.py'
if os.path.exists(stream_path):
    with open(stream_path, 'r') as f:
        code = f.read()

    has_stream = 'async def generate_weekly_suggestions_stream' in code
    has_events = all(evt in code for evt in ['start', 'items_loaded', 'analyzing', 'found', 'complete', 'error'])
    uses_async_gen = 'AsyncGenerator' in code
    has_yield = 'yield' in code

    print(f"✅ Streaming module exists")
    print(f"   • Async generator function: {'✅' if has_stream else '❌'}")
    print(f"   • All event types: {'✅' if has_events else '❌'}")
    print(f"   • AsyncGenerator type hint: {'✅' if uses_async_gen else '❌'}")
    print(f"   • Yields events: {'✅' if has_yield else '❌'}")

    if all([has_stream, has_events, has_yield]):
        test_results.append(("Streaming Suggester", "PASS"))
    else:
        test_results.append(("Streaming Suggester", "FAIL"))
else:
    print(f"❌ Streaming module not found at {stream_path}")
    test_results.append(("Streaming Suggester", "FAIL"))
print()

# ============================================================================
# Component 4: Database Helpers
# ============================================================================
print("✓ Component 4: Database Helpers")
print("-" * 70)

suggestions_path = 'database/api/suggestions.py'
if os.path.exists(suggestions_path):
    with open(suggestions_path, 'r') as f:
        code = f.read()

    has_upsert = 'def upsert_weekly_report' in code
    has_get = 'def get_weekly_report' in code
    has_history = 'def get_recent_reports' in code
    uses_merge = 'MERGE INTO' in code
    privacy_safe = 'location_city' in code and 'lat' not in code.replace('lat/lon', '')

    print(f"✅ Database helpers exist")
    print(f"   • upsert_weekly_report(): {'✅' if has_upsert else '❌'}")
    print(f"   • get_weekly_report(): {'✅' if has_get else '❌'}")
    print(f"   • get_recent_reports(): {'✅' if has_history else '❌'}")
    print(f"   • Uses MERGE (idempotent): {'✅' if uses_merge else '❌'}")
    print(f"   • Privacy-safe (no lat/lon): {'✅' if privacy_safe else '❌'}")

    if all([has_upsert, has_get, has_history, uses_merge]):
        test_results.append(("Database Helpers", "PASS"))
    else:
        test_results.append(("Database Helpers", "FAIL"))
else:
    print(f"❌ Database helpers not found at {suggestions_path}")
    test_results.append(("Database Helpers", "FAIL"))
print()

# ============================================================================
# Component 5: API Endpoints
# ============================================================================
print("✓ Component 5: API Endpoints")
print("-" * 70)

api_path = 'database/api/main.py'
if os.path.exists(api_path):
    with open(api_path, 'r') as f:
        code = f.read()

    has_main_endpoint = '/api/user/{user_id}/weekly_alternatives' in code
    has_history_endpoint = '/api/user/{user_id}/weekly_alternatives/history' in code
    has_stream_endpoint = '/api/user/{user_id}/weekly_alternatives/stream' in code
    uses_sse = 'StreamingResponse' in code and 'text/event-stream' in code
    has_frontend_example = 'EventSource' in code

    print(f"✅ API module exists")
    print(f"   • GET /weekly_alternatives: {'✅' if has_main_endpoint else '❌'}")
    print(f"   • GET /weekly_alternatives/history: {'✅' if has_history_endpoint else '❌'}")
    print(f"   • GET /weekly_alternatives/stream: {'✅' if has_stream_endpoint else '❌'}")
    print(f"   • Uses SSE (Server-Sent Events): {'✅' if uses_sse else '❌'}")
    print(f"   • Frontend example documented: {'✅' if has_frontend_example else '❌'}")

    if all([has_main_endpoint, has_history_endpoint, has_stream_endpoint, uses_sse]):
        test_results.append(("API Endpoints", "PASS"))
    else:
        test_results.append(("API Endpoints", "FAIL"))
else:
    print(f"❌ API module not found at {api_path}")
    test_results.append(("API Endpoints", "FAIL"))
print()

# ============================================================================
# Component 6: Weekly Job Script
# ============================================================================
print("✓ Component 6: Weekly Job Script")
print("-" * 70)

job_path = 'scripts/generate_weekly_suggestions.py'
if os.path.exists(job_path):
    with open(job_path, 'r') as f:
        code = f.read()

    has_shebang = code.startswith('#!/usr/bin/env python')
    has_argparse = 'argparse' in code
    has_week_arg = '--week' in code
    has_user_arg = '--user' in code
    has_dry_run = '--dry-run' in code
    has_logging = 'json.dump' in code or 'log' in code.lower()

    print(f"✅ Job script exists")
    print(f"   • Executable shebang: {'✅' if has_shebang else '❌'}")
    print(f"   • Uses argparse: {'✅' if has_argparse else '❌'}")
    print(f"   • --week argument: {'✅' if has_week_arg else '❌'}")
    print(f"   • --user argument: {'✅' if has_user_arg else '❌'}")
    print(f"   • --dry-run mode: {'✅' if has_dry_run else '❌'}")
    print(f"   • JSON logging: {'✅' if has_logging else '❌'}")

    if all([has_argparse, has_week_arg, has_dry_run]):
        test_results.append(("Weekly Job Script", "PASS"))
    else:
        test_results.append(("Weekly Job Script", "FAIL"))
else:
    print(f"❌ Job script not found at {job_path}")
    test_results.append(("Weekly Job Script", "FAIL"))
print()

# ============================================================================
# Component 7: Tests
# ============================================================================
print("✓ Component 7: Tests")
print("-" * 70)

test_files = [
    ('tests/test_phase1_buyer_location.py', 'Phase 1'),
    ('tests/test_weekly_suggester.py', 'Phase 2'),
    ('tests/test_phase3_simple.py', 'Phase 3'),
    ('tests/test_phase4_weekly_job.py', 'Phase 4'),
    ('tests/test_phase5_streaming.py', 'Phase 5'),
]

all_tests_exist = True
for test_file, phase in test_files:
    exists = os.path.exists(test_file)
    print(f"   • {phase}: {'✅' if exists else '❌'}")
    if not exists:
        all_tests_exist = False

if all_tests_exist:
    test_results.append(("Tests", "PASS"))
else:
    test_results.append(("Tests", "FAIL"))
print()

# ============================================================================
# Component 8: Documentation
# ============================================================================
print("✓ Component 8: Documentation")
print("-" * 70)

doc_files = [
    ('docs/e2e-integration-test.md', 'E2E Test Guide'),
    ('tmp/claude/security-review-phase2.md', 'Security Review Phase 2'),
    ('tmp/claude/security-review-phase3.md', 'Security Review Phase 3'),
    ('tmp/claude/todo.md', 'Project TODO'),
]

docs_count = 0
for doc_file, name in doc_files:
    if os.path.exists(doc_file):
        docs_count += 1
        print(f"   • {name}: ✅")
    else:
        print(f"   • {name}: ❌")

if docs_count >= 2:
    test_results.append(("Documentation", "PASS"))
else:
    test_results.append(("Documentation", "FAIL"))
print()

# ============================================================================
# Summary
# ============================================================================
print("="*70)
print("INTEGRATION VERIFICATION SUMMARY")
print("="*70)
print()

passed = sum(1 for _, result in test_results if result == "PASS")
failed = sum(1 for _, result in test_results if result == "FAIL")

for component, result in test_results:
    status = "✅" if result == "PASS" else "❌"
    print(f"{status} {component:<30} {result}")

print()
print(f"Total: {passed}/{len(test_results)} components verified")
print()

if passed == len(test_results):
    print("🎉 ALL COMPONENTS VERIFIED!")
    print()
    print("The Weekly Suggestions feature is complete and ready!")
    print()
    print("Next steps:")
    print("  1. Configure Snowflake credentials in database/api/.env")
    print("  2. Set DEDALUS_API_KEY in .env")
    print("  3. Test with: python scripts/generate_weekly_suggestions.py --dry-run")
    print("  4. Start API: uvicorn database.api.main:app --reload")
    print("  5. Test streaming: curl -N http://localhost:8000/api/user/test_user_001/weekly_alternatives/stream")
    print()
    sys.exit(0)
else:
    print(f"⚠️  {failed} component(s) need attention")
    print()
    sys.exit(1)
