#!/usr/bin/env python3
"""Test 04: IPC - Verify SEND, RECV, BROADCAST, REGISTER syscalls"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

# Worker agent that receives and responds to messages
WORKER_SCRIPT = """
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    # Register with a name
    client.register_name("ipc-worker")

    # Process messages for 10 seconds
    for i in range(20):
        result = client.recv_messages(max_messages=10)
        messages = result.get("messages", [])

        for msg in messages:
            # Send response back
            response = {"status": "processed", "original": msg.get("message", {})}
            client.send_message(response, to=msg.get("from_id"))

        time.sleep(0.5)
"""

def main():
    print("=== Test 04: IPC (Inter-Process Communication) ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Set permissions to unrestricted to allow spawn
            print("--- Test 4.0: Set Spawn Permissions ---")
            perm_result = client.set_permissions(level="unrestricted")
            if perm_result.get("success"):
                print("  Permissions set to 'unrestricted' (spawn enabled)")
                print("  PASSED\n")
            else:
                print(f"  SKIP - Could not set permissions: {perm_result.get('error')}")
                print("  IPC tests require 'unrestricted' permission level for spawning")
                return 0

            # Create worker script
            with open('/tmp/ipc_worker.py', 'w') as f:
                f.write(WORKER_SCRIPT)

            # Test 1: Register name
            print("--- Test 4.1: Register Name ---")
            result = client.register_name("ipc-main")

            if result.get("success"):
                print(f"  Registered as: ipc-main")
                print(f"  Agent ID: {result.get('agent_id')}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 2: Spawn worker agent
            print("--- Test 4.2: Spawn Worker ---")
            spawn_result = client.spawn(
                name="ipc-worker",
                script="/tmp/ipc_worker.py",
                sandboxed=False
            )

            if spawn_result and spawn_result.get('id'):
                worker_id = spawn_result.get('id')
                print(f"  Worker spawned: ID={worker_id}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {spawn_result}")
                return 1

            time.sleep(2)  # Wait for worker to register

            # Test 3: Send message by name
            print("--- Test 4.3: Send Message by Name ---")
            msg = {"task": "process", "data": [1, 2, 3]}
            result = client.send_message(msg, to_name="ipc-worker")

            if result.get("success"):
                print(f"  Sent to 'ipc-worker': {msg}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                client.kill(agent_id=worker_id)
                return 1

            # Test 4: Send message by ID
            print("--- Test 4.4: Send Message by ID ---")
            msg = {"task": "calculate", "value": 42}
            result = client.send_message(msg, to=worker_id)

            if result.get("success"):
                print(f"  Sent to agent {worker_id}: {msg}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                client.kill(agent_id=worker_id)
                return 1

            time.sleep(1)  # Wait for responses

            # Test 5: Receive messages
            print("--- Test 4.5: Receive Messages ---")
            result = client.recv_messages(max_messages=10)

            if result.get("success"):
                messages = result.get("messages", [])
                count = result.get("count", len(messages))
                print(f"  Received {count} message(s)")
                for msg in messages[:3]:
                    print(f"    From {msg.get('from_id')}: {msg.get('message', {})}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                client.kill(agent_id=worker_id)
                return 1

            # Test 6: Broadcast message
            print("--- Test 4.6: Broadcast Message ---")
            result = client.broadcast({"event": "shutdown_warning"}, include_self=False)

            if result.get("success"):
                delivered = result.get("delivered_count", 0)
                print(f"  Broadcast delivered to {delivered} agent(s)")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                client.kill(agent_id=worker_id)
                return 1

            # Cleanup
            print("--- Cleanup ---")
            client.kill(agent_id=worker_id)
            os.remove('/tmp/ipc_worker.py')
            print("  Worker killed and script removed\n")

            print("=== Test 04 PASSED ===")
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
