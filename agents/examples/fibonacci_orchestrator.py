#!/usr/bin/env python3
"""
Fibonacci Orchestrator - AgentOS Test Script

Demonstrates using a SINGLE LLM prompt to:
1. Create a folder via terminal command
2. Generate a Python file with Fibonacci (recursion + DP)
3. Test both implementations

This showcases AgentOS as an AI agent runtime that can orchestrate
complex multi-step tasks through natural language.
"""

import sys
import os
import subprocess
import json
import re

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

# The single comprehensive prompt
ORCHESTRATION_PROMPT = """You are an AI agent that executes tasks. I need you to generate a complete plan with executable code.

TASK: Create a test environment for Fibonacci implementations.

Generate your response in this EXACT JSON format (no markdown, just raw JSON):
{
    "mkdir_command": "the shell command to create a folder called 'fibonacci_test' in /tmp",
    "python_file_content": "the complete Python file content with both recursive and DP Fibonacci implementations plus test code",
    "python_filename": "fibonacci.py",
    "run_command": "the command to run the Python file"
}

Requirements for the Python file:
1. A recursive Fibonacci function called `fib_recursive(n)`
2. A dynamic programming Fibonacci function called `fib_dp(n)` using memoization or tabulation
3. A main block that:
   - Tests both functions for n = 0, 1, 5, 10, 20
   - Compares their outputs to verify correctness
   - Prints timing comparison for n=30 to show DP is faster
   - Prints "ALL TESTS PASSED" if everything works

Output ONLY the JSON, nothing else."""


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling potential markdown wrapping."""
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    json_match = re.search(r'\{[^{}]*"mkdir_command"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response:\n{text[:500]}...")


def run_command(cmd: str, description: str) -> tuple[bool, str]:
    """Run a shell command and return (success, output)."""
    print(f"\n{'='*60}")
    print(f"EXECUTING: {description}")
    print(f"COMMAND: {cmd}")
    print('='*60)

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0

        if output.strip():
            print(output)

        if success:
            print(f"✓ {description} completed successfully")
        else:
            print(f"✗ {description} failed with code {result.returncode}")

        return success, output
    except subprocess.TimeoutExpired:
        print(f"✗ {description} timed out")
        return False, "Timeout"
    except Exception as e:
        print(f"✗ {description} error: {e}")
        return False, str(e)


def main():
    print("=" * 60)
    print("AgentOS Fibonacci Orchestrator")
    print("Single-Prompt Task Orchestration Demo")
    print("=" * 60)
    print()

    print("[1] Connecting to AgentOS kernel...")

    with AgentOSClient() as client:
        print("    Connected!")
        print()

        # Step 1: Send the single orchestration prompt
        print("[2] Sending orchestration prompt to LLM...")
        print("-" * 40)
        print("PROMPT:")
        print(ORCHESTRATION_PROMPT[:200] + "...")
        print("-" * 40)

        result = client.think(
            ORCHESTRATION_PROMPT,
            system_instruction="You are a precise code generator. Output only valid JSON with no extra text.",
            temperature=0.2  # Low temperature for deterministic output
        )

        if result.get("error"):
            print(f"\n✗ LLM Error: {result['error']}")
            return 1

        response_text = result.get("content", "")
        print(f"\n[3] Received LLM response ({len(response_text)} chars)")

        if result.get("tokens"):
            print(f"    Tokens used: {result['tokens']}")

        # Step 2: Parse the JSON response
        print("\n[4] Parsing LLM response...")
        try:
            plan = extract_json(response_text)
            print("    JSON parsed successfully!")
            print(f"    - mkdir_command: {plan.get('mkdir_command', 'N/A')}")
            print(f"    - python_filename: {plan.get('python_filename', 'N/A')}")
            print(f"    - run_command: {plan.get('run_command', 'N/A')}")
        except ValueError as e:
            print(f"\n✗ Failed to parse JSON: {e}")
            print("\nRaw response:")
            print(response_text)
            return 1

        # Step 3: Execute the plan
        print("\n[5] Executing the plan...")

        # 3a: Create the folder
        mkdir_cmd = plan.get("mkdir_command", "mkdir -p /tmp/fibonacci_test")
        success, _ = run_command(mkdir_cmd, "Create folder")
        if not success:
            return 1

        # 3b: Write the Python file
        python_content = plan.get("python_file_content", "")
        python_filename = plan.get("python_filename", "fibonacci.py")
        filepath = f"/tmp/fibonacci_test/{python_filename}"

        print(f"\n{'='*60}")
        print(f"WRITING: Python file to {filepath}")
        print('='*60)

        try:
            with open(filepath, 'w') as f:
                f.write(python_content)
            print(f"✓ Wrote {len(python_content)} bytes to {filepath}")

            # Show the generated code
            print("\n--- Generated Python Code ---")
            print(python_content)
            print("--- End of Code ---\n")
        except Exception as e:
            print(f"✗ Failed to write file: {e}")
            return 1

        # 3c: Run the Python file
        run_cmd = plan.get("run_command", f"python3 {filepath}")
        # Ensure we use the correct path
        if "/tmp/fibonacci_test" not in run_cmd:
            run_cmd = f"python3 {filepath}"

        success, output = run_command(run_cmd, "Run Fibonacci tests")

        # Step 4: Summary
        print("\n" + "=" * 60)
        print("ORCHESTRATION SUMMARY")
        print("=" * 60)
        print(f"✓ Connected to AgentOS kernel")
        print(f"✓ Sent single orchestration prompt to LLM")
        print(f"✓ Created folder: /tmp/fibonacci_test")
        print(f"✓ Generated Python file with recursive + DP Fibonacci")
        print(f"{'✓' if success else '✗'} Executed tests")

        if "ALL TESTS PASSED" in output or "PASSED" in output.upper():
            print("\n🎉 ALL FIBONACCI TESTS PASSED!")
            return 0
        else:
            print("\n⚠ Tests completed (check output above)")
            return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
