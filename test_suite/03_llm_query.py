#!/usr/bin/env python3
"""Test 03: LLM Query - Verify THINK syscall with Gemini API"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def main():
    print("=== Test 03: LLM Query ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Test 1: Simple query
            print("--- Test 3.1: Simple Query ---")
            result = client.think("What is 2 + 2? Reply with just the number.")

            if result.get("success"):
                content = result.get("content", "")
                print(f"  Question: What is 2 + 2?")
                print(f"  Response: {content[:100]}...")
                if "4" in content:
                    print("  PASSED\n")
                else:
                    print("  WARNING - Expected '4' in response\n")
            else:
                error = result.get("error", "")
                if "API key" in error or "not configured" in error.lower():
                    print("  SKIP - LLM not configured (no API key)")
                    print("  Set GEMINI_API_KEY environment variable\n")
                    return 0  # Skip, don't fail
                else:
                    print(f"  FAILED - {error}")
                    return 1

            # Test 2: Query with system instruction
            print("--- Test 3.2: Query with System Instruction ---")
            result = client.think(
                "Hello!",
                system_instruction="You are a pirate. Always respond like a pirate."
            )

            if result.get("success"):
                content = result.get("content", "")
                print(f"  System: You are a pirate...")
                print(f"  Response: {content[:150]}...")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 3: Query with temperature
            print("--- Test 3.3: Query with Temperature ---")
            result = client.think(
                "Give me a random word.",
                temperature=1.5
            )

            if result.get("success"):
                content = result.get("content", "")
                print(f"  Temperature: 1.5 (high creativity)")
                print(f"  Response: {content[:100]}...")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}")
                return 1

            # Test 4: Check response structure
            print("--- Test 3.4: Response Structure ---")
            result = client.think("Say 'test'")

            required_fields = ["success", "content"]
            missing = [f for f in required_fields if f not in result]

            if not missing:
                print(f"  Has required fields: {required_fields}")
                if "tokens" in result:
                    print(f"  Token count: {result.get('tokens', {})}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - Missing fields: {missing}")
                return 1

            print("=== Test 03 PASSED ===")
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
