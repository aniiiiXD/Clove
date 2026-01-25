#!/usr/bin/env python3
"""Test 05: Shell Execution - Verify EXEC syscall"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 05: Shell Execution ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Test 1: Simple command
            print("--- Test 5.1: Simple Command ---")
            result = client.exec("echo 'Hello from Clove'")

            if result.get("success"):
                stdout = result.get("stdout", "").strip()
                exit_code = result.get("exit_code", -1)
                print(f"  Command: echo 'Hello from Clove'")
                print(f"  Output: {stdout}")
                print(f"  Exit code: {exit_code}")
                if exit_code == 0 and "Hello from Clove" in stdout:
                    print("  PASSED\n")
                else:
                    print("  FAILED - Unexpected output")
                    return 1
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 2: Command with pipes
            print("--- Test 5.2: Command with Pipes ---")
            result = client.exec("echo 'line1\nline2\nline3' | wc -l")

            if result.get("success"):
                stdout = result.get("stdout", "").strip()
                print(f"  Command: echo ... | wc -l")
                print(f"  Output: {stdout}")
                if "3" in stdout:
                    print("  PASSED\n")
                else:
                    print("  FAILED - Expected 3 lines")
                    return 1
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 3: Command with working directory
            print("--- Test 5.3: Command with Working Directory ---")
            result = client.exec("pwd", cwd="/tmp")

            if result.get("success"):
                stdout = result.get("stdout", "").strip()
                print(f"  Command: pwd (cwd=/tmp)")
                print(f"  Output: {stdout}")
                if "/tmp" in stdout:
                    print("  PASSED\n")
                else:
                    print("  FAILED - Expected /tmp")
                    return 1
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 4: Command that fails
            print("--- Test 5.4: Command That Fails ---")
            result = client.exec("ls /nonexistent_directory_12345")

            exit_code = result.get("exit_code", 0)
            stderr = result.get("stderr", "")
            print(f"  Command: ls /nonexistent_directory_12345")
            print(f"  Exit code: {exit_code}")
            print(f"  Stderr: {stderr[:100]}...")
            if exit_code != 0:
                print("  PASSED (command failed as expected)\n")
            else:
                print("  FAILED - Expected non-zero exit code")
                return 1

            # Test 5: Command with timeout
            print("--- Test 5.5: Command with Timeout ---")
            result = client.exec("sleep 1 && echo 'done'", timeout=5)

            if result.get("success"):
                stdout = result.get("stdout", "").strip()
                print(f"  Command: sleep 1 && echo 'done' (timeout=5s)")
                print(f"  Output: {stdout}")
                if "done" in stdout:
                    print("  PASSED\n")
                else:
                    print("  FAILED - Command should have completed")
                    return 1
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 6: Environment variables
            print("--- Test 5.6: Environment Variables ---")
            result = client.exec("echo $HOME")

            if result.get("success"):
                stdout = result.get("stdout", "").strip()
                print(f"  Command: echo $HOME")
                print(f"  Output: {stdout}")
                if stdout and "/" in stdout:
                    print("  PASSED\n")
                else:
                    print("  WARNING - HOME not set\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            print("=== Test 05 PASSED ===")
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
