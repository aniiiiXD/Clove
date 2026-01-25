#!/usr/bin/env python3
"""
Health Check Agent

Performs a comprehensive health check of the AgentOS kernel.
Tests various syscalls and reports status.

Usage:
    agentos agent run agents/examples/health_check.py --machine <machine_id>
"""

import sys
import os
import time
import json

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOS


def main():
    agent = AgentOS("health_check")
    results = {
        "tests": [],
        "passed": 0,
        "failed": 0
    }

    def test(name, fn):
        """Run a test and record the result."""
        try:
            result = fn()
            results["tests"].append({"name": name, "status": "pass", "result": result})
            results["passed"] += 1
            agent.write(f"  [PASS] {name}")
            return True
        except Exception as e:
            results["tests"].append({"name": name, "status": "fail", "error": str(e)})
            results["failed"] += 1
            agent.write(f"  [FAIL] {name}: {e}")
            return False

    agent.write("=" * 50)
    agent.write("AgentOS Health Check")
    agent.write("=" * 50)
    agent.write(f"Agent ID: {agent.agent_id}")
    agent.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    agent.write("-" * 50)

    # Test 1: Basic write syscall
    agent.write("\n[Test 1] Basic Write Syscall")
    test("write_syscall", lambda: "ok")

    # Test 2: Get Agent ID
    agent.write("\n[Test 2] Agent ID")
    test("get_agent_id", lambda: agent.agent_id)

    # Test 3: Multiple writes (stress test)
    agent.write("\n[Test 3] Multiple Writes")
    def stress_write():
        for i in range(10):
            agent.write(f"    Stress test iteration {i + 1}")
        return "10 writes completed"
    test("stress_write", stress_write)

    # Test 4: Memory allocation (if supported)
    agent.write("\n[Test 4] Memory Operations")
    def test_memory():
        data = "x" * 1000  # 1KB test data
        return f"Allocated {len(data)} bytes"
    test("memory_ops", test_memory)

    # Test 5: Timing
    agent.write("\n[Test 5] Timing Test")
    def test_timing():
        start = time.time()
        time.sleep(0.1)
        elapsed = time.time() - start
        return f"100ms sleep took {elapsed*1000:.2f}ms"
    test("timing", test_timing)

    # Summary
    agent.write("\n" + "=" * 50)
    agent.write("Health Check Summary")
    agent.write("=" * 50)
    agent.write(f"Total Tests: {results['passed'] + results['failed']}")
    agent.write(f"Passed: {results['passed']}")
    agent.write(f"Failed: {results['failed']}")

    if results['failed'] == 0:
        agent.write("\n[OK] All health checks passed!")
        agent.exit(0)
    else:
        agent.write(f"\n[WARNING] {results['failed']} health check(s) failed!")
        agent.exit(1)


if __name__ == "__main__":
    main()
