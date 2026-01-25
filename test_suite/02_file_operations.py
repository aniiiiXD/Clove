#!/usr/bin/env python3
"""Test 02: File Operations - Verify READ and WRITE syscalls"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 02: File Operations ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            test_file = "/tmp/clove_test_file.txt"
            test_content = "Hello from Clove!\nLine 2\nLine 3"

            # Test 1: Write file
            print("--- Test 2.1: Write File ---")
            result = client.write_file(test_file, test_content)

            if result.get("success"):
                bytes_written = result.get("bytes_written", 0)
                print(f"  File: {test_file}")
                print(f"  Bytes written: {bytes_written}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 2: Read file
            print("--- Test 2.2: Read File ---")
            result = client.read_file(test_file)

            if result.get("success"):
                content = result.get("content", "")
                size = result.get("size", 0)
                print(f"  Size: {size} bytes")
                print(f"  Content matches: {content.strip() == test_content}")
                if content.strip() == test_content:
                    print("  PASSED\n")
                else:
                    print(f"  FAILED - Content mismatch")
                    print(f"  Expected: {repr(test_content)}")
                    print(f"  Got: {repr(content)}")
                    return 1
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 3: Append to file
            print("--- Test 2.3: Append to File ---")
            append_content = "\nLine 4 (appended)"
            result = client.write_file(test_file, append_content, mode="append")

            if result.get("success"):
                print(f"  Appended {result.get('bytes_written', 0)} bytes")

                # Verify append
                result = client.read_file(test_file)
                if result.get("success") and "Line 4" in result.get("content", ""):
                    print("  Append verified")
                    print("  PASSED\n")
                else:
                    print("  FAILED - Append not verified")
                    return 1
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 4: Read non-existent file
            print("--- Test 2.4: Read Non-Existent File ---")
            result = client.read_file("/tmp/this_file_does_not_exist_12345.txt")

            if not result.get("success"):
                print(f"  Error (expected): {result.get('error', 'file not found')}")
                print("  PASSED\n")
            else:
                print("  FAILED - Should have returned error")
                return 1

            # Test 5: Write to nested path
            print("--- Test 2.5: Write to Nested Path ---")
            nested_file = "/tmp/clove_test/nested/file.txt"

            # Create directory first via exec
            client.exec(f"mkdir -p /tmp/clove_test/nested")

            result = client.write_file(nested_file, "nested content")
            if result.get("success"):
                print(f"  Created: {nested_file}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Cleanup
            print("--- Cleanup ---")
            os.remove(test_file)
            client.exec("rm -rf /tmp/clove_test")
            print("  Test files removed\n")

            print("=== Test 02 PASSED ===")
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
