#!/usr/bin/env python3
"""Test 10: State Store - Verify key-value store operations"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 10: State Store ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0  # Skip, don't fail

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            test_key = "test:state:key"
            test_value = {"message": "Hello from test", "number": 123, "nested": {"a": 1}}

            # Test 1: Store a value
            print("--- Test 10.1: Store Value ---")
            result = client.store(test_key, test_value, scope="global")
            print(f"Result: {result}")

            if result.get("success"):
                print(f"  Stored key: {test_key}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 2: Fetch the value
            print("--- Test 10.2: Fetch Value ---")
            result = client.fetch(test_key)
            print(f"Result: {result}")

            if result.get("success") and result.get("exists"):
                fetched = result.get("value")
                print(f"  Fetched: {fetched}")
                if fetched == test_value:
                    print("  Values match!")
                    print("  PASSED\n")
                else:
                    print("  FAILED - Values don't match\n")
                    return 1
            else:
                print(f"  FAILED - {result.get('error', 'Key not found')}\n")
                return 1

            # Test 3: Store with TTL
            print("--- Test 10.3: Store with TTL ---")
            result = client.store("test:ttl:key", "expires soon", ttl=60)
            print(f"Result: {result}")

            if result.get("success"):
                print("  Stored with 60s TTL")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 4: List keys
            print("--- Test 10.4: List Keys ---")
            result = client.list_keys(prefix="test:")
            print(f"Result: {result}")

            if result.get("success"):
                keys = result.get("keys", [])
                print(f"  Found {len(keys)} key(s) with prefix 'test:'")
                for key in keys:
                    print(f"    - {key}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 5: Delete key
            print("--- Test 10.5: Delete Key ---")
            result = client.delete_key(test_key)
            print(f"Result: {result}")

            if result.get("success"):
                print(f"  Deleted: {result.get('deleted', False)}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 6: Verify deletion
            print("--- Test 10.6: Verify Deletion ---")
            result = client.fetch(test_key)
            print(f"Result: {result}")

            if result.get("success") and not result.get("exists", True):
                print("  Key no longer exists")
                print("  PASSED\n")
            elif not result.get("exists", True):
                print("  Key no longer exists")
                print("  PASSED\n")
            else:
                print("  FAILED - Key still exists after deletion\n")
                return 1

            # Cleanup: Delete TTL key
            client.delete_key("test:ttl:key")

            print("=== Test 10 PASSED ===")
            return 0

    except ConnectionRefusedError:
        print("SKIP - Cannot connect to kernel")
        return 0
    except Exception as e:
        print(f"ERROR - {e}")
        return 1

if __name__ == "__main__":
    exit(main())
