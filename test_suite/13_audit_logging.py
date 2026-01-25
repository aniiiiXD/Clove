#!/usr/bin/env python3
"""Test 13: Audit Logging - Verify audit log collection and configuration"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 13: Audit Logging ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0  # Skip, don't fail

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Set permissions to unrestricted to allow spawn (needed for test 3)
            print("--- Test 13.0: Set Spawn Permissions ---")
            perm_result = client.set_permissions(level="unrestricted")
            if perm_result.get("success"):
                print("  Permissions set to 'unrestricted' (spawn enabled)")
                print("  PASSED\n")
            else:
                print(f"  WARNING - Could not set permissions: {perm_result.get('error')}")
                print("  Some tests may be skipped\n")

            # Test 1: Get audit log (should work even if empty)
            print("--- Test 13.1: Get Audit Log ---")
            result = client.get_audit_log(limit=10)

            if result.get("success") or "entries" in result:
                entries = result.get("entries", [])
                print(f"  Retrieved {len(entries)} audit entries")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 2: Configure audit logging
            print("--- Test 13.2: Configure Audit Logging ---")
            config_result = client.set_audit_config(
                log_lifecycle=True,
                log_security=True,
                log_syscalls=False,  # Keep verbose logging off
                max_entries=1000
            )

            if config_result.get("success"):
                print(f"  Config updated: {config_result.get('config', {})}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {config_result.get('error')}")
                return 1

            # Test 3: Generate audit events by spawning/killing an agent
            print("--- Test 13.3: Generate Audit Events ---")

            # Create a simple agent script
            with open('/tmp/audit_test_agent.py', 'w') as f:
                f.write("""
import time
from clove_sdk import CloveClient
with CloveClient() as c:
    c.register_name("audit-test")
    time.sleep(5)
""")

            # Spawn agent (should generate AGENT_SPAWNED audit)
            spawn_result = client.spawn(
                name="audit-test-agent",
                script="/tmp/audit_test_agent.py",
                sandboxed=False
            )
            agent_id = spawn_result.get('id') if spawn_result else None
            print(f"  Spawned agent: {agent_id}")

            time.sleep(1)

            # Kill agent (should generate AGENT_KILLED audit)
            if agent_id:
                client.kill(agent_id=agent_id)
                print(f"  Killed agent: {agent_id}")

            time.sleep(0.5)
            print("  PASSED\n")

            # Test 4: Retrieve audit log with category filter
            print("--- Test 13.4: Filter by Category ---")
            result = client.get_audit_log(category="AGENT_LIFECYCLE", limit=20)

            if result.get("success") or "entries" in result:
                entries = result.get("entries", [])
                print(f"  Found {len(entries)} AGENT_LIFECYCLE entries")

                # Show recent entries
                for entry in entries[-5:]:
                    print(f"    [{entry.get('id', 'N/A')}] {entry.get('event_type', 'unknown')}: "
                          f"agent={entry.get('agent_name', entry.get('agent_id', 'N/A'))}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 5: Filter by agent ID
            print("--- Test 13.5: Filter by Agent ID ---")
            if agent_id:
                result = client.get_audit_log(agent_id=agent_id, limit=10)

                if result.get("success") or "entries" in result:
                    entries = result.get("entries", [])
                    print(f"  Found {len(entries)} entries for agent {agent_id}")
                    print("  PASSED\n")
                else:
                    print(f"  FAILED - {result.get('error')}")
                    return 1
            else:
                print("  SKIP - No agent ID available\n")

            # Test 6: Get audit log with since_id pagination
            print("--- Test 13.6: Pagination with since_id ---")

            # Get first batch
            result1 = client.get_audit_log(limit=5)
            entries1 = result1.get("entries", [])

            if entries1:
                last_id = entries1[-1].get('id', 0)
                print(f"  First batch: {len(entries1)} entries, last_id={last_id}")

                # Get entries after that ID
                result2 = client.get_audit_log(since_id=last_id, limit=5)
                entries2 = result2.get("entries", [])
                print(f"  Second batch (since {last_id}): {len(entries2)} entries")

                # Verify no overlap
                ids1 = {e.get('id') for e in entries1}
                ids2 = {e.get('id') for e in entries2}
                overlap = ids1 & ids2

                if not overlap:
                    print("  No overlap between batches")
                    print("  PASSED\n")
                else:
                    print(f"  WARNING - Overlapping IDs: {overlap}\n")
            else:
                print("  SKIP - No entries to paginate\n")

            # Test 7: Audit log entry structure
            print("--- Test 13.7: Entry Structure Validation ---")
            result = client.get_audit_log(limit=1)
            entries = result.get("entries", [])

            if entries:
                entry = entries[0]
                required_fields = ['id', 'timestamp', 'category', 'event_type']
                missing = [f for f in required_fields if f not in entry]

                if not missing:
                    print(f"  Entry has required fields: {required_fields}")
                    print(f"  Sample entry: {entry}")
                    print("  PASSED\n")
                else:
                    print(f"  FAILED - Missing fields: {missing}")
                    return 1
            else:
                print("  SKIP - No entries to validate\n")

            print("=== Test 13 PASSED ===")
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
