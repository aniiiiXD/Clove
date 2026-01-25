#!/usr/bin/env python3
"""Test 01: Basic Connection - Verify kernel connectivity and NOOP syscall"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 01: Basic Connection ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0  # Skip, don't fail

    try:
        # Test 1: Connect to kernel
        print("--- Test 1.1: Connect to Kernel ---")
        client = CloveClient()
        if client.connect():
            print("  Connected successfully")
            print("  PASSED\n")
        else:
            print("  FAILED - Could not connect")
            return 1

        # Test 2: NOOP/Echo syscall
        print("--- Test 1.2: NOOP (Echo) Syscall ---")
        test_message = "Hello, Clove Kernel!"
        response = client.noop(test_message)

        if response:
            print(f"  Sent: {test_message}")
            print(f"  Received: {response}")
            if test_message in response:
                print("  PASSED\n")
            else:
                print("  FAILED - Response mismatch")
                client.disconnect()
                return 1
        else:
            print("  FAILED - No response")
            client.disconnect()
            return 1

        # Test 3: Multiple NOOP calls
        print("--- Test 1.3: Multiple NOOP Calls ---")
        for i in range(5):
            msg = f"Test message {i+1}"
            resp = client.noop(msg)
            if not resp or msg not in resp:
                print(f"  FAILED at message {i+1}")
                client.disconnect()
                return 1
        print("  5 consecutive NOOP calls successful")
        print("  PASSED\n")

        # Test 4: Agent ID assignment
        print("--- Test 1.4: Agent ID Assignment ---")
        agent_id = client.agent_id
        print(f"  Assigned agent ID: {agent_id}")
        if agent_id > 0:
            print("  PASSED\n")
        else:
            print("  WARNING - Agent ID is 0 (may be expected)\n")

        # Cleanup
        client.disconnect()

        print("=== Test 01 PASSED ===")
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
