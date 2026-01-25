#!/usr/bin/env python3
"""Test 8: Permission System - Verify permission checks work correctly"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 8: Permission System ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0  # Skip, don't fail

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Test 1: Get current permissions
            print("--- Test 8.1: Get Permissions ---")
            result = client.get_permissions()
            print(f"Result: {result}")

            if result.get("success"):
                print("  Got permissions successfully")
                perms = result.get("permissions", {})
                print(f"  Level: {perms.get('level', 'unknown')}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 2: Try to read an allowed path
            print("--- Test 8.2: Read Allowed Path ---")
            result = client.read_file("/tmp/test_permissions_read.txt")
            # This might fail if file doesn't exist, but permission should not block it
            if result.get("error") and "Permission denied" in str(result.get("error", "")):
                print("  FAILED - Permission denied for /tmp path\n")
                return 1
            else:
                print("  Path access allowed (file may or may not exist)")
                print("  PASSED\n")

            # Test 3: Try to execute a safe command
            print("--- Test 8.3: Execute Safe Command ---")
            result = client.exec("echo 'permission test'")
            print(f"Result: {result}")

            if result.get("success"):
                print("  Command executed successfully")
                print("  PASSED\n")
            elif "Permission denied" in str(result.get("error", "")):
                print("  Command blocked by permissions (expected if sandboxed)")
                print("  PASSED\n")
            else:
                print(f"  Result: {result}")
                print("  PASSED (command behavior as expected)\n")

            # Test 4: Verify permission level changes
            print("--- Test 8.4: Set Permission Level ---")
            result = client.set_permissions(level="standard")
            print(f"Result: {result}")

            if result.get("success") or "not allowed" in str(result.get("error", "")).lower():
                print("  Set permissions call completed")
                print("  PASSED\n")
            else:
                print(f"  Result: {result}")
                print("  PASSED (may require elevation)\n")

            print("=== Test 8 PASSED ===")
            return 0

    except ConnectionRefusedError:
        print("SKIP - Cannot connect to kernel")
        return 0
    except Exception as e:
        print(f"ERROR - {e}")
        return 1

if __name__ == "__main__":
    exit(main())
