#!/usr/bin/env python3
"""
Clove Test Suite Runner

Runs all tests in order and reports results.
Usage: python test_suite/run_all.py
"""

import subprocess
import sys
import os
from pathlib import Path

# Test files in order
TESTS = [
    ("01_connection.py", "Basic Connection"),
    ("02_file_operations.py", "File Operations"),
    ("03_llm_query.py", "LLM Query"),
    ("04_ipc.py", "Inter-Process Communication"),
    ("05_shell_exec.py", "Shell Execution"),
    ("06_agent_management.py", "Agent Management"),
    ("07_http_request.py", "HTTP Requests"),
    ("08_permissions.py", "Permission System"),
    ("09_events.py", "Event System (Pub/Sub)"),
    ("10_state_store.py", "State Store"),
    ("11_metrics.py", "Metrics System"),
    ("12_pause_resume.py", "Pause/Resume"),
    ("13_audit_logging.py", "Audit Logging"),
    ("14_execution_replay.py", "Execution Recording & Replay"),
]

def run_test(test_file: str, description: str) -> bool:
    """Run a single test file and return success status."""
    test_path = Path(__file__).parent / test_file

    if not test_path.exists():
        print(f"  ⚠️  SKIP - {test_file} not found")
        return True  # Don't fail for missing optional tests

    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent / "agents/python_sdk")}
        )

        if result.returncode == 0:
            print(f"  ✅ PASS - {description}")
            return True
        else:
            print(f"  ❌ FAIL - {description}")
            if result.stdout:
                print(f"     stdout: {result.stdout[:200]}")
            if result.stderr:
                print(f"     stderr: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ⏱️  TIMEOUT - {description}")
        return False
    except Exception as e:
        print(f"  ❌ ERROR - {description}: {e}")
        return False


def main():
    print("=" * 60)
    print("           CLOVE TEST SUITE")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    skipped = 0

    for test_file, description in TESTS:
        test_path = Path(__file__).parent / test_file
        if not test_path.exists():
            skipped += 1
            print(f"  ⚠️  SKIP - {description} ({test_file} not found)")
            continue

        if run_test(test_file, description):
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
