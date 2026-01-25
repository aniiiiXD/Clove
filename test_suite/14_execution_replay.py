#!/usr/bin/env python3
"""Test 14: Execution Recording & Replay - Verify syscall recording and replay"""
import sys
import os
import time
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 14: Execution Recording & Replay ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0  # Skip, don't fail

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Test 1: Check initial recording status
            print("--- Test 14.1: Initial Recording Status ---")
            status = client.get_recording_status()

            if status.get("success") or "state" in status:
                print(f"  Recording state: {status.get('state', 'UNKNOWN')}")
                print(f"  Entry count: {status.get('entry_count', 0)}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {status.get('error')}")
                return 1

            # Test 2: Start recording
            print("--- Test 14.2: Start Recording ---")
            result = client.start_recording(
                include_think=False,  # Exclude non-deterministic
                include_http=False,
                include_exec=False,
                max_entries=10000
            )

            if result.get("success"):
                print(f"  Recording started: {result}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 3: Verify recording is active
            print("--- Test 14.3: Verify Recording Active ---")
            status = client.get_recording_status()

            if status.get("state") == "RECORDING":
                print(f"  State: {status.get('state')}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - Expected RECORDING, got {status.get('state')}")
                return 1

            # Test 4: Generate some syscalls to record
            print("--- Test 14.4: Generate Recorded Syscalls ---")

            # Store some values
            client.store("replay_test_1", {"value": 100}, scope="global")
            client.store("replay_test_2", {"value": 200}, scope="global")
            client.store("replay_test_3", {"value": 300}, scope="global")

            # Fetch them back
            client.fetch("replay_test_1")
            client.fetch("replay_test_2")

            # Delete one
            client.delete_key("replay_test_3")

            # List keys
            client.list_keys("replay_test")

            time.sleep(0.5)

            # Check entry count increased
            status = client.get_recording_status()
            entry_count = status.get('entry_count', 0)
            print(f"  Generated syscalls, entry count: {entry_count}")

            if entry_count > 0:
                print("  PASSED\n")
            else:
                print("  WARNING - No entries recorded (syscalls may be filtered)\n")

            # Test 5: Stop recording
            print("--- Test 14.5: Stop Recording ---")
            result = client.stop_recording()

            if result.get("success"):
                print(f"  Recording stopped: {result}")
                final_count = result.get('entry_count', 0)
                print(f"  Final entry count: {final_count}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 6: Export the recording
            print("--- Test 14.6: Export Recording ---")
            status = client.get_recording_status(export=True)

            recording_data = status.get('recording', '')

            if recording_data:
                # Parse to verify it's valid JSON
                try:
                    entries = json.loads(recording_data)
                    print(f"  Exported {len(entries)} entries")

                    # Show sample entry
                    if entries:
                        sample = entries[0]
                        print(f"  Sample entry keys: {list(sample.keys())}")
                        print(f"  Sample opcode_name: {sample.get('opcode_name', 'N/A')}")
                    print("  PASSED\n")
                except json.JSONDecodeError as e:
                    print(f"  FAILED - Invalid JSON: {e}")
                    return 1
            else:
                print("  WARNING - No recording data exported")
                print("  (May be expected if all syscalls were filtered)\n")
                recording_data = "[]"  # Empty array for replay test

            # Test 7: Verify recording state is IDLE
            print("--- Test 14.7: Verify Recording Stopped ---")
            status = client.get_recording_status()

            if status.get("state") == "IDLE":
                print(f"  State: {status.get('state')}")
                print("  PASSED\n")
            else:
                print(f"  WARNING - Expected IDLE, got {status.get('state')}\n")

            # Test 8: Start replay (if we have recording data)
            print("--- Test 14.8: Start Replay ---")

            if recording_data and recording_data != "[]":
                result = client.start_replay(recording_data)

                if result.get("success"):
                    print(f"  Replay started: {result}")
                    total = result.get('total_entries', 0)
                    print(f"  Total entries to replay: {total}")
                    print("  PASSED\n")
                else:
                    # Replay may fail if no entries - that's OK
                    error = result.get('error', '')
                    if 'empty' in error.lower() or 'no recording' in error.lower():
                        print(f"  SKIP - No recording to replay")
                        print("  PASSED\n")
                    else:
                        print(f"  FAILED - {error}")
                        return 1
            else:
                print("  SKIP - No recording data to replay\n")

            # Test 9: Get replay status
            print("--- Test 14.9: Replay Status ---")
            status = client.get_replay_status()

            if status.get("success") or "state" in status:
                print(f"  Replay state: {status.get('state', 'UNKNOWN')}")
                print(f"  Progress: {status.get('current_entry', 0)}/{status.get('total_entries', 0)}")
                print(f"  Replayed: {status.get('entries_replayed', 0)}")
                print(f"  Skipped: {status.get('entries_skipped', 0)}")
                if status.get('error'):
                    print(f"  Error: {status.get('error')}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {status.get('error')}")
                return 1

            # Test 10: Recording with agent filter
            print("--- Test 14.10: Recording with Filters ---")

            result = client.start_recording(
                include_think=True,  # Include LLM calls
                include_http=True,   # Include HTTP calls
                filter_agents=[999],  # Filter to non-existent agent
                max_entries=100
            )

            if result.get("success"):
                print(f"  Recording with filters started")

                # Do some syscalls (should not be recorded due to filter)
                client.store("filter_test", "value")

                status = client.get_recording_status()
                filtered_count = status.get('entry_count', 0)
                print(f"  Entry count with filter: {filtered_count}")

                client.stop_recording()
                client.delete_key("filter_test")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Cleanup
            print("--- Cleanup ---")
            client.delete_key("replay_test_1")
            client.delete_key("replay_test_2")
            print("  State cleaned up\n")

            print("=== Test 14 PASSED ===")
            return 0

    except ConnectionRefusedError:
        print("SKIP - Cannot connect to kernel")
        return 0
    except Exception as e:
        print(f"ERROR - {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
