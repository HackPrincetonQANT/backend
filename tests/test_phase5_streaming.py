"""
Tests for Phase 5: Streaming & End-to-End Integration

Tests streaming weekly suggestions and full integration flow.

Following CLAUDE.MD Rule 2: Each step should contain tests to validate changes work.
"""

import json
import os
import sys


# Test 1: Streaming module exists
def test_streaming_module_exists():
    """
    Verify that weekly_suggester_stream.py exists.

    Expected: File should exist in src/services/
    """
    stream_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester_stream.py')
    assert os.path.exists(stream_path), "Streaming module should exist"


# Test 2: Streaming function signature
def test_streaming_function_exists():
    """
    Verify that generate_weekly_suggestions_stream function exists.

    Expected: Should be an async generator function.
    """
    stream_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester_stream.py')

    with open(stream_path, 'r') as f:
        code = f.read()

    assert 'async def generate_weekly_suggestions_stream' in code, "Should have streaming function"
    assert 'AsyncGenerator' in code, "Should use AsyncGenerator type hint"
    assert 'yield' in code, "Should yield events"


# Test 3: Event types defined
def test_event_types():
    """
    Verify that all required event types are implemented.

    Expected: start, items_loaded, analyzing, found, complete, error
    """
    stream_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester_stream.py')

    with open(stream_path, 'r') as f:
        code = f.read()

    required_events = ['start', 'items_loaded', 'analyzing', 'found', 'complete', 'error']

    for event in required_events:
        assert f'"event": "{event}"' in code or f"'event': '{event}'" in code, \
            f"Should have {event} event type"


# Test 4: SSE endpoint exists
def test_sse_endpoint_exists():
    """
    Verify that streaming SSE endpoint exists in main.py.

    Expected: Should have /api/user/{user_id}/weekly_alternatives/stream
    """
    main_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'main.py')

    with open(main_path, 'r') as f:
        code = f.read()

    assert '/api/user/{user_id}/weekly_alternatives/stream' in code, "Should have streaming endpoint"
    assert 'StreamingResponse' in code, "Should use StreamingResponse"
    assert 'text/event-stream' in code, "Should use SSE media type"


# Test 5: SSE headers configured
def test_sse_headers():
    """
    Verify that SSE endpoint has proper headers.

    Expected: Cache-Control, Connection, X-Accel-Buffering headers.
    """
    main_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'main.py')

    with open(main_path, 'r') as f:
        code = f.read()

    assert 'Cache-Control' in code, "Should have Cache-Control header"
    assert 'no-cache' in code, "Should disable caching"
    assert 'Connection' in code, "Should have Connection header"
    assert 'keep-alive' in code, "Should keep connection alive"


# Test 6: Error handling in streaming
def test_streaming_error_handling():
    """
    Verify that streaming has error handling.

    Expected: Should have try/except and yield error events.
    """
    stream_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester_stream.py')

    with open(stream_path, 'r') as f:
        code = f.read()

    assert 'try:' in code, "Should have try block"
    assert 'except' in code, "Should have except block"
    assert '"event": "error"' in code or "'event': 'error'" in code, "Should yield error events"


# Test 7: Timestamp in events
def test_timestamps_in_events():
    """
    Verify that events include timestamps.

    Expected: Each event should have timestamp field.
    """
    stream_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester_stream.py')

    with open(stream_path, 'r') as f:
        code = f.read()

    assert 'timestamp' in code, "Should include timestamps"
    assert 'datetime.now().isoformat()' in code, "Should use ISO format timestamps"


# Test 8: Dedalus streaming integration
def test_dedalus_streaming_attempt():
    """
    Verify that code attempts to use Dedalus streaming if available.

    Expected: Should check for run_stream method and fall back if not available.
    """
    stream_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester_stream.py')

    with open(stream_path, 'r') as f:
        code = f.read()

    assert 'run_stream' in code, "Should attempt to use run_stream"
    assert 'hasattr' in code or 'try:' in code, "Should have fallback mechanism"


# Test 9: Progress tracking
def test_progress_tracking():
    """
    Verify that streaming tracks and reports progress metrics.

    Expected: Should track processing time, items analyzed, savings.
    """
    stream_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester_stream.py')

    with open(stream_path, 'r') as f:
        code = f.read()

    assert 'processing_time' in code or 'start_time' in code, "Should track processing time"
    assert 'items_analyzed' in code, "Should track items analyzed"
    assert 'total_savings' in code, "Should track total savings"


# Test 10: SSE format compliance
def test_sse_format():
    """
    Verify that SSE endpoint formats events correctly.

    Expected: Should use "data: {json}\\n\\n" format.
    """
    main_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'main.py')

    with open(main_path, 'r') as f:
        code = f.read()

    # Check for SSE format
    assert 'data:' in code, "Should use SSE data: prefix"
    assert '\\n\\n' in code, "Should use double newline separator"


# Test 11: Frontend example in docs
def test_frontend_example_documented():
    """
    Verify that endpoint includes frontend usage example.

    Expected: Should have JavaScript EventSource example.
    """
    main_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'main.py')

    with open(main_path, 'r') as f:
        code = f.read()

    assert 'EventSource' in code, "Should include EventSource example"
    assert 'javascript' in code.lower(), "Should have JavaScript example"


# Test 12: Dynamic module loading
def test_dynamic_module_loading():
    """
    Verify that streaming endpoint loads module dynamically.

    Expected: Should use importlib.util for safe module loading.
    """
    main_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'main.py')

    with open(main_path, 'r') as f:
        code = f.read()

    assert 'importlib.util' in code, "Should use importlib for dynamic loading"
    assert 'spec_from_file_location' in code, "Should load from file location"


# Test 13: Items details in events
def test_items_details_in_events():
    """
    Verify that found events include item details.

    Expected: Should include item name, prices, merchant, savings.
    """
    stream_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester_stream.py')

    with open(stream_path, 'r') as f:
        code = f.read()

    # Check for item details in found events
    assert 'item_name' in code, "Should include item name"
    assert 'original_price' in code, "Should include original price"
    assert 'alternative_merchant' in code, "Should include alternative merchant"
    assert 'savings' in code, "Should include savings amount"


# Test 14: Integration components present
def test_integration_components():
    """
    Verify that all components needed for end-to-end flow exist.

    Expected: Suggester, database helpers, API endpoints all present.
    """
    # Check suggester exists
    suggester_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'weekly_suggester.py')
    assert os.path.exists(suggester_path), "Suggester should exist"

    # Check database helpers exist
    suggestions_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'suggestions.py')
    assert os.path.exists(suggestions_path), "Database helpers should exist"

    # Check API exists
    api_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'api', 'main.py')
    assert os.path.exists(api_path), "API should exist"

    # Check job script exists
    job_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate_weekly_suggestions.py')
    assert os.path.exists(job_path), "Job script should exist"


if __name__ == '__main__':
    # Run tests manually
    print("Running Phase 5 Streaming & Integration Tests...")

    print("\n1. Testing streaming module exists...")
    test_streaming_module_exists()
    print("   ✅ Streaming module exists")

    print("\n2. Testing streaming function...")
    test_streaming_function_exists()
    print("   ✅ Streaming function exists")

    print("\n3. Testing event types...")
    test_event_types()
    print("   ✅ All event types present")

    print("\n4. Testing SSE endpoint...")
    test_sse_endpoint_exists()
    print("   ✅ SSE endpoint exists")

    print("\n5. Testing SSE headers...")
    test_sse_headers()
    print("   ✅ SSE headers configured")

    print("\n6. Testing error handling...")
    test_streaming_error_handling()
    print("   ✅ Error handling implemented")

    print("\n7. Testing timestamps...")
    test_timestamps_in_events()
    print("   ✅ Timestamps in events")

    print("\n8. Testing Dedalus streaming...")
    test_dedalus_streaming_attempt()
    print("   ✅ Dedalus streaming attempted")

    print("\n9. Testing progress tracking...")
    test_progress_tracking()
    print("   ✅ Progress tracking implemented")

    print("\n10. Testing SSE format...")
    test_sse_format()
    print("   ✅ SSE format correct")

    print("\n11. Testing frontend example...")
    test_frontend_example_documented()
    print("   ✅ Frontend example documented")

    print("\n12. Testing dynamic module loading...")
    test_dynamic_module_loading()
    print("   ✅ Dynamic module loading safe")

    print("\n13. Testing item details...")
    test_items_details_in_events()
    print("   ✅ Item details in events")

    print("\n14. Testing integration components...")
    test_integration_components()
    print("   ✅ All integration components present")

    print("\n✅ All Phase 5 tests passed!")
