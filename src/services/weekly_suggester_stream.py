"""
Weekly Suggestions Stream Service - Real-Time Progress Updates

Provides streaming version of weekly alternative suggestions with real-time progress.
Uses Dedalus AI streaming capabilities to show live updates as AI discovers alternatives.

Design Principles (CLAUDE.MD):
- Real-time user feedback (streaming)
- Graceful error handling
- Type safety
"""

import asyncio
import importlib.util
import json
import os
import sys
import re
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Dynamically load modules
def load_module(module_name: str, file_path: str):
    """Dynamically load a Python module"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load weekly suggester for helper functions
suggester_path = os.path.join(os.path.dirname(__file__), 'weekly_suggester.py')
suggester = load_module('weekly_suggester', suggester_path)

# Import from weekly suggester
from dedalus_labs import AsyncDedalus, DedalusRunner


async def generate_weekly_suggestions_stream(
    user_id: str,
    week_start: str,
    top_n: int = 5
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream weekly alternative suggestions with real-time progress updates.

    Yields progress events as AI discovers alternatives:
    - start: Beginning analysis
    - items_loaded: Purchases fetched
    - analyzing: Analyzing specific item
    - searching: Searching retailers
    - found: Alternative discovered
    - complete: Analysis finished
    - error: Error occurred

    Args:
        user_id: User identifier
        week_start: ISO week start date (YYYY-MM-DD)
        top_n: Number of top items to analyze (default 5)

    Yields:
        Dict events with progress updates

    Example events:
        {"event": "start", "message": "Analyzing your purchases..."}
        {"event": "found", "item": "Ring Doorbell", "savings": 20.00}
        {"event": "complete", "total_savings": 45.50}
    """
    start_time = datetime.now()

    try:
        # Validate week_start format
        try:
            datetime.strptime(week_start, '%Y-%m-%d')
        except ValueError:
            yield {
                "event": "error",
                "message": f"Invalid week format: {week_start}",
                "timestamp": datetime.now().isoformat()
            }
            return

        # Event 1: Start
        yield {
            "event": "start",
            "message": "Fetching your purchases...",
            "user_id": user_id,
            "week_start": week_start,
            "timestamp": datetime.now().isoformat()
        }

        # Step 1: Fetch top expensive items
        items = suggester.fetch_top_items(user_id, week_start, limit=top_n)

        if not items:
            # Event: No purchases
            yield {
                "event": "complete",
                "message": "No purchases found for this week",
                "items_analyzed": 0,
                "items_with_alternatives": 0,
                "total_savings": 0.0,
                "timestamp": datetime.now().isoformat()
            }
            return

        # Event 2: Items loaded
        yield {
            "event": "items_loaded",
            "count": len(items),
            "message": f"Found {len(items)} purchases to analyze",
            "items": [
                {"name": item['item_name'], "price": item['price']}
                for item in items
            ],
            "timestamp": datetime.now().isoformat()
        }

        # Step 2: Build Plan prompt
        prompt = suggester.build_plan_prompt(items)

        # Event 3: Starting AI analysis
        yield {
            "event": "analyzing",
            "message": "AI is searching for cheaper alternatives...",
            "timestamp": datetime.now().isoformat()
        }

        # Step 3: Stream AI response
        client = AsyncDedalus()
        runner = DedalusRunner(client)

        ai_response_chunks = []

        # Stream with Dedalus (if streaming is available)
        try:
            # Try streaming first
            if hasattr(runner, 'run_stream'):
                async for chunk in runner.run_stream(
                    input=prompt,
                    model="openai/gpt-4o-mini"
                ):
                    # Accumulate chunks
                    ai_response_chunks.append(chunk)

                    # Event: Progress chunk
                    yield {
                        "event": "progress",
                        "chunk": chunk,
                        "timestamp": datetime.now().isoformat()
                    }

                # Combine all chunks
                full_response = "".join(ai_response_chunks)
            else:
                # Fallback: Regular run (non-streaming)
                response = await runner.run(
                    input=prompt,
                    model="openai/gpt-4o-mini"
                )
                full_response = response.final_output

        except Exception as e:
            # Event: AI error
            yield {
                "event": "error",
                "message": f"AI processing error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return

        # Step 4: Parse findings
        try:
            # Try to parse as JSON
            findings = json.loads(full_response)
            if not isinstance(findings, list):
                # Try to extract JSON array from response
                json_match = re.search(r'\[\s*\{.*\}\s*\]', full_response, re.DOTALL)
                if json_match:
                    findings = json.loads(json_match.group(0))
                else:
                    findings = []
        except (json.JSONDecodeError, AttributeError):
            findings = []

        # Event 4: Emit each finding as it's discovered
        total_savings = 0.0
        for finding in findings:
            savings = finding.get('total_savings', 0.0)
            total_savings += savings

            yield {
                "event": "found",
                "item_name": finding.get('item_name', 'Unknown'),
                "original_price": finding.get('original_price', 0.0),
                "original_merchant": finding.get('original_merchant', 'Unknown'),
                "alternative_merchant": finding.get('alternative_merchant', 'Unknown'),
                "alternative_price": finding.get('alternative_price', 0.0),
                "total_landed_cost": finding.get('total_landed_cost', 0.0),
                "savings": savings,
                "url": finding.get('url', ''),
                "timestamp": datetime.now().isoformat()
            }

        # Step 5: Complete
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        yield {
            "event": "complete",
            "message": "Analysis complete!",
            "items_analyzed": len(items),
            "items_with_alternatives": len(findings),
            "total_savings": round(total_savings, 2),
            "processing_time_seconds": round(processing_time, 2),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # Event: Unexpected error
        yield {
            "event": "error",
            "message": f"Unexpected error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


async def main():
    """Test the streaming suggester"""
    print("Testing Streaming Weekly Suggester...")
    print("=" * 70)

    user_id = "test_user_001"
    week_start = "2024-01-22"

    async for event in generate_weekly_suggestions_stream(user_id, week_start):
        event_type = event.get('event', 'unknown')

        if event_type == 'start':
            print(f"\n🚀 {event['message']}")

        elif event_type == 'items_loaded':
            print(f"\n📦 {event['message']}")
            for item in event['items']:
                print(f"   • {item['name']} - ${item['price']:.2f}")

        elif event_type == 'analyzing':
            print(f"\n🔍 {event['message']}")

        elif event_type == 'progress':
            print(f"   {event['chunk']}", end='', flush=True)

        elif event_type == 'found':
            print(f"\n✅ Found alternative for {event['item_name']}")
            print(f"   Original: ${event['original_price']:.2f} at {event['original_merchant']}")
            print(f"   Alternative: ${event['total_landed_cost']:.2f} at {event['alternative_merchant']}")
            print(f"   💰 Savings: ${event['savings']:.2f}")

        elif event_type == 'complete':
            print(f"\n{'=' * 70}")
            print(f"✅ {event['message']}")
            print(f"Items analyzed: {event['items_analyzed']}")
            print(f"Alternatives found: {event['items_with_alternatives']}")
            print(f"Total potential savings: ${event['total_savings']:.2f}")
            print(f"Processing time: {event['processing_time_seconds']:.1f}s")
            print(f"{'=' * 70}\n")

        elif event_type == 'error':
            print(f"\n❌ Error: {event['message']}")

    print("Streaming test complete!")


if __name__ == '__main__':
    asyncio.run(main())
