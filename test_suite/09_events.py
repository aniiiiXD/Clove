#!/usr/bin/env python3
"""Test 9: Event System - Verify pub/sub events work correctly"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 9: Event System (Pub/Sub) ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0  # Skip, don't fail

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Test 1: Subscribe to events
            print("--- Test 9.1: Subscribe to Events ---")
            event_types = ["AGENT_SPAWNED", "AGENT_EXITED", "CUSTOM"]
            result = client.subscribe(event_types)
            print(f"Result: {result}")

            if result.get("success"):
                print(f"  Subscribed to: {result.get('subscribed', [])}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 2: Emit a custom event
            print("--- Test 9.2: Emit Custom Event ---")
            result = client.emit_event("CUSTOM", {"test_key": "test_value", "count": 42})
            print(f"Result: {result}")

            if result.get("success"):
                print(f"  Event delivered to {result.get('delivered_to', 0)} subscriber(s)")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 3: Poll for events
            print("--- Test 9.3: Poll Events ---")
            result = client.poll_events(max_events=10)
            print(f"Result: {result}")

            if result.get("success"):
                events = result.get("events", [])
                print(f"  Received {len(events)} event(s)")
                for i, event in enumerate(events):
                    print(f"    [{i}] Type: {event.get('type')}, Data: {event.get('data')}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 4: Unsubscribe from events
            print("--- Test 9.4: Unsubscribe from Events ---")
            result = client.unsubscribe(["CUSTOM"])
            print(f"Result: {result}")

            if result.get("success"):
                print(f"  Unsubscribed from: {result.get('unsubscribed', [])}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            print("=== Test 9 PASSED ===")
            return 0

    except ConnectionRefusedError:
        print("SKIP - Cannot connect to kernel")
        return 0
    except Exception as e:
        print(f"ERROR - {e}")
        return 1

if __name__ == "__main__":
    exit(main())
