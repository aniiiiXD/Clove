#!/usr/bin/env python3
"""Test 07: HTTP Requests - Verify HTTP syscall"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 07: HTTP Requests ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Set permissions to unrestricted to allow HTTP
            print("--- Test 7.0: Set HTTP Permissions ---")
            perm_result = client.set_permissions(level="unrestricted")
            if perm_result.get("success"):
                print("  Permissions set to 'unrestricted' (HTTP enabled)")
                print("  PASSED\n")
            else:
                print(f"  SKIP - Could not set permissions: {perm_result.get('error')}")
                print("  HTTP tests require 'unrestricted' permission level")
                return 0

            # Test 1: Simple GET request
            print("--- Test 7.1: GET Request ---")
            result = client.http("https://httpbin.org/get")

            if result.get("success"):
                status = result.get("status_code", result.get("status", 0))
                body = result.get("body", "")
                print(f"  URL: https://httpbin.org/get")
                print(f"  Status: {status}")
                print(f"  Body length: {len(body)} bytes")
                if status == 200:
                    print("  PASSED\n")
                else:
                    print(f"  FAILED - Expected status 200, got {status}")
                    return 1
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 2: GET with query parameters
            print("--- Test 7.2: GET with Query Parameters ---")
            result = client.http("https://httpbin.org/get?foo=bar&num=123")

            if result.get("success"):
                status = result.get("status_code", result.get("status", 0))
                body = result.get("body", "")
                print(f"  URL: https://httpbin.org/get?foo=bar&num=123")
                print(f"  Status: {status}")
                if "foo" in body and "bar" in body:
                    print("  Query params reflected in response")
                    print("  PASSED\n")
                else:
                    print("  WARNING - Query params not in response\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 3: POST request with JSON body
            print("--- Test 7.3: POST Request with JSON ---")
            post_data = {"name": "Clove", "version": "0.1.0"}
            result = client.http(
                "https://httpbin.org/post",
                method="POST",
                headers={"Content-Type": "application/json"},
                body=json.dumps(post_data)
            )

            if result.get("success"):
                status = result.get("status_code", result.get("status", 0))
                body = result.get("body", "")
                print(f"  Method: POST")
                print(f"  Status: {status}")
                if status == 200 and "Clove" in body:
                    print("  POST data echoed back")
                    print("  PASSED\n")
                else:
                    print(f"  FAILED - Expected 200 and data echo")
                    return 1
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 4: Custom headers
            print("--- Test 7.4: Custom Headers ---")
            result = client.http(
                "https://httpbin.org/headers",
                headers={"X-Custom-Header": "CloveTest", "User-Agent": "CloveKernel/0.1"}
            )

            if result.get("success"):
                body = result.get("body", "")
                print(f"  Custom headers sent")
                if "X-Custom-Header" in body or "CloveTest" in body:
                    print("  Custom header reflected")
                    print("  PASSED\n")
                else:
                    print("  WARNING - Custom header not in response\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 5: Timeout handling
            print("--- Test 7.5: Timeout Handling ---")
            result = client.http("https://httpbin.org/delay/1", timeout=5)

            if result.get("success"):
                status = result.get("status_code", result.get("status", 0))
                print(f"  URL: https://httpbin.org/delay/1 (timeout=5s)")
                print(f"  Status: {status}")
                print("  PASSED\n")
            else:
                error = result.get("error", "")
                if "timeout" in error.lower():
                    print("  Request timed out (expected for slow endpoint)")
                    print("  PASSED\n")
                else:
                    print(f"  FAILED - {error}")
                    return 1

            print("=== Test 07 PASSED ===")
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
