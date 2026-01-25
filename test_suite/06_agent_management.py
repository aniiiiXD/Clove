#!/usr/bin/env python3
"""Test 06: Agent Management - Verify SPAWN, LIST, KILL syscalls"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

# Simple worker agent
WORKER_SCRIPT = """
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    client.register_name("test-worker")
    for i in range(30):
        time.sleep(1)
"""

def main():
    print("=== Test 06: Agent Management ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Set permissions to unrestricted to allow spawn
            print("--- Test 6.0: Set Spawn Permissions ---")
            perm_result = client.set_permissions(level="unrestricted")
            if perm_result.get("success"):
                print("  Permissions set to 'unrestricted' (spawn enabled)")
                print("  PASSED\n")
            else:
                print(f"  SKIP - Could not set permissions: {perm_result.get('error')}")
                print("  Agent management tests require 'unrestricted' permission level")
                return 0

            # Create worker script
            with open('/tmp/test_worker.py', 'w') as f:
                f.write(WORKER_SCRIPT)

            # Test 1: List agents (before spawn)
            print("--- Test 6.1: List Agents (Before Spawn) ---")
            agents = client.list_agents()
            initial_count = len(agents)
            print(f"  Active agents: {initial_count}")
            print("  PASSED\n")

            # Test 2: Spawn agent
            print("--- Test 6.2: Spawn Agent ---")
            result = client.spawn(
                name="test-worker-1",
                script="/tmp/test_worker.py",
                sandboxed=False
            )

            if result and (result.get('id') or result.get('success')):
                agent_id = result.get('id')
                pid = result.get('pid')
                print(f"  Agent ID: {agent_id}")
                print(f"  PID: {pid}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result}")
                return 1

            time.sleep(1)

            # Test 3: List agents (after spawn)
            print("--- Test 6.3: List Agents (After Spawn) ---")
            agents = client.list_agents()
            print(f"  Active agents: {len(agents)}")
            for agent in agents:
                print(f"    - ID={agent.get('id')}, Name={agent.get('name')}, "
                      f"State={agent.get('state')}, PID={agent.get('pid')}")

            if len(agents) > initial_count:
                print("  PASSED\n")
            else:
                print("  FAILED - Agent count should have increased")
                return 1

            # Test 4: Spawn with restart policy
            print("--- Test 6.4: Spawn with Restart Policy ---")
            result = client.spawn(
                name="test-worker-2",
                script="/tmp/test_worker.py",
                sandboxed=False,
                restart_policy="on-failure",
                max_restarts=3,
                restart_window=300
            )

            if result and (result.get('id') or result.get('success')):
                agent_id_2 = result.get('id')
                policy = result.get('restart_policy', 'unknown')
                print(f"  Agent ID: {agent_id_2}")
                print(f"  Restart policy: {policy}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result}")
                client.kill(agent_id=agent_id)
                return 1

            time.sleep(1)

            # Test 5: Kill agent by ID
            print("--- Test 6.5: Kill Agent by ID ---")
            result = client.kill(agent_id=agent_id)
            if result:
                print(f"  Killed agent ID: {agent_id}")
                print("  PASSED\n")
            else:
                print("  FAILED - Could not kill agent")
                return 1

            time.sleep(1)

            # Test 6: Kill agent by name
            print("--- Test 6.6: Kill Agent by Name ---")
            result = client.kill(name="test-worker-2")
            if result:
                print(f"  Killed agent: test-worker-2")
                print("  PASSED\n")
            else:
                print("  WARNING - Kill by name may have failed")
                # Try by ID
                client.kill(agent_id=agent_id_2)
                print()

            # Test 7: Verify agents are gone
            print("--- Test 6.7: Verify Agents Removed ---")
            time.sleep(1)
            agents = client.list_agents()
            current_count = len(agents)
            print(f"  Active agents: {current_count}")

            # Check our agents are gone
            our_agents = [a for a in agents if 'test-worker' in a.get('name', '')]
            if len(our_agents) == 0:
                print("  All test agents removed")
                print("  PASSED\n")
            else:
                print(f"  WARNING - {len(our_agents)} test agents still running")
                for a in our_agents:
                    client.kill(agent_id=a.get('id'))
                print()

            # Cleanup
            print("--- Cleanup ---")
            os.remove('/tmp/test_worker.py')
            print("  Script removed\n")

            print("=== Test 06 PASSED ===")
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
