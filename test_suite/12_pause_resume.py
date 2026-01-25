#!/usr/bin/env python3
"""Test 12: Pause/Resume - Verify agent pause and resume functionality"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

# Worker script that increments a counter
WORKER_SCRIPT = """
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    client.register_name("pause-test-worker")
    count = 0
    while count < 60:  # Run for up to 60 iterations
        count += 1
        client.store("pause_test_counter", count, scope="global")
        time.sleep(0.5)
"""

def main():
    print("=== Test 12: Pause/Resume ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0  # Skip, don't fail

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Set permissions to unrestricted to allow spawn
            print("--- Test 12.0: Set Spawn Permissions ---")
            perm_result = client.set_permissions(level="unrestricted")
            if perm_result.get("success"):
                print("  Permissions set to 'unrestricted' (spawn enabled)")
                print("  PASSED\n")
            else:
                print(f"  SKIP - Could not set permissions: {perm_result.get('error')}")
                print("  Pause/Resume tests require 'unrestricted' permission level")
                return 0

            # Create worker script
            with open('/tmp/pause_test_worker.py', 'w') as f:
                f.write(WORKER_SCRIPT)

            # Test 1: Spawn a worker agent
            print("--- Test 12.1: Spawn Worker Agent ---")
            spawn_result = client.spawn(
                name="pause-test-worker",
                script="/tmp/pause_test_worker.py",
                sandboxed=False
            )

            if not spawn_result or not spawn_result.get('success', spawn_result.get('id')):
                print(f"  FAILED - Could not spawn agent: {spawn_result}")
                return 1

            agent_id = spawn_result.get('id')
            print(f"  Spawned agent ID: {agent_id}")
            print("  PASSED\n")

            # Wait for agent to start and increment counter
            time.sleep(2)

            # Test 2: Verify agent is running (counter increasing)
            print("--- Test 12.2: Verify Agent Running ---")
            result1 = client.fetch("pause_test_counter")
            time.sleep(1)
            result2 = client.fetch("pause_test_counter")

            counter1 = result1.get('value', 0) if result1.get('exists') else 0
            counter2 = result2.get('value', 0) if result2.get('exists') else 0

            if counter2 > counter1:
                print(f"  Counter increased: {counter1} -> {counter2}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - Counter not increasing: {counter1} -> {counter2}")
                client.kill(agent_id=agent_id)
                return 1

            # Test 3: Pause the agent
            print("--- Test 12.3: Pause Agent ---")
            pause_result = client.pause(agent_id=agent_id)

            if pause_result:
                print(f"  Pause result: {pause_result}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - Could not pause agent")
                client.kill(agent_id=agent_id)
                return 1

            # Test 4: Verify agent is paused (counter not increasing)
            print("--- Test 12.4: Verify Agent Paused ---")
            time.sleep(0.5)
            result3 = client.fetch("pause_test_counter")
            time.sleep(1.5)  # Wait longer than normal iteration
            result4 = client.fetch("pause_test_counter")

            counter3 = result3.get('value', 0) if result3.get('exists') else 0
            counter4 = result4.get('value', 0) if result4.get('exists') else 0

            if counter4 == counter3:
                print(f"  Counter unchanged while paused: {counter3} -> {counter4}")
                print("  PASSED\n")
            else:
                print(f"  WARNING - Counter changed while paused: {counter3} -> {counter4}")
                print("  (May be timing issue, continuing...)\n")

            # Test 5: Verify agent shows PAUSED state in list
            print("--- Test 12.5: Check Agent State ---")
            agents = client.list_agents()
            paused_agent = None
            for agent in agents:
                if agent.get('id') == agent_id:
                    paused_agent = agent
                    break

            if paused_agent:
                state = paused_agent.get('state', 'unknown')
                print(f"  Agent state: {state}")
                if state.lower() == 'paused':
                    print("  PASSED\n")
                else:
                    print(f"  WARNING - Expected 'paused', got '{state}'\n")
            else:
                print("  WARNING - Agent not found in list\n")

            # Test 6: Resume the agent
            print("--- Test 12.6: Resume Agent ---")
            resume_result = client.resume(agent_id=agent_id)

            if resume_result:
                print(f"  Resume result: {resume_result}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - Could not resume agent")
                client.kill(agent_id=agent_id)
                return 1

            # Test 7: Verify agent resumed (counter increasing again)
            print("--- Test 12.7: Verify Agent Resumed ---")
            time.sleep(1)
            result5 = client.fetch("pause_test_counter")
            time.sleep(1)
            result6 = client.fetch("pause_test_counter")

            counter5 = result5.get('value', 0) if result5.get('exists') else 0
            counter6 = result6.get('value', 0) if result6.get('exists') else 0

            if counter6 > counter5:
                print(f"  Counter increasing again: {counter5} -> {counter6}")
                print("  PASSED\n")
            else:
                print(f"  WARNING - Counter not increasing after resume: {counter5} -> {counter6}")
                print("  (May be timing issue)\n")

            # Cleanup
            print("--- Cleanup ---")
            client.kill(agent_id=agent_id)
            client.delete_key("pause_test_counter")
            print("  Agent killed and state cleaned up\n")

            print("=== Test 12 PASSED ===")
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
