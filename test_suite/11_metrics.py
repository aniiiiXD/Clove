#!/usr/bin/env python3
"""Test 11: Metrics System - Verify system and agent metrics collection"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
from clove_sdk import CloveClient

def format_bytes(b):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"

def main():
    print("=== Test 11: Metrics System ===\n")

    # Check if kernel socket exists
    if not os.path.exists('/tmp/clove.sock'):
        print("SKIP - Kernel not running (/tmp/clove.sock not found)")
        print("   Start kernel with: ./build/clove_kernel")
        return 0  # Skip, don't fail

    try:
        with CloveClient() as client:
            print("Connected to kernel\n")

            # Test 1: Get system metrics
            print("--- Test 11.1: System Metrics ---")
            result = client.get_system_metrics()

            if result.get("success"):
                metrics = result.get("metrics", {})
                cpu = metrics.get("cpu", {})
                mem = metrics.get("memory", {})
                disk = metrics.get("disk", {})
                net = metrics.get("network", {})

                print(f"  CPU: {cpu.get('percent', 0):.1f}% ({cpu.get('count', 0)} cores)")
                print(f"  Load: {cpu.get('load_avg', [0,0,0])}")
                print(f"  Memory: {format_bytes(mem.get('used', 0))} / {format_bytes(mem.get('total', 0))} ({mem.get('percent', 0):.1f}%)")
                print(f"  Disk I/O: R={format_bytes(disk.get('read_bytes', 0))} W={format_bytes(disk.get('write_bytes', 0))}")
                print(f"  Network: Sent={format_bytes(net.get('bytes_sent', 0))} Recv={format_bytes(net.get('bytes_recv', 0))}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 2: Get all agent metrics (may be empty)
            print("--- Test 11.2: All Agent Metrics ---")
            result = client.get_all_agent_metrics()

            if result.get("success"):
                agents = result.get("agents", [])
                print(f"  Found {len(agents)} agent(s)")
                for agent in agents[:5]:  # Show first 5
                    proc = agent.get("process", {})
                    print(f"    - {agent.get('name', 'unknown')} (PID={agent.get('pid', 0)}): "
                          f"CPU={proc.get('cpu', {}).get('percent', 0):.1f}%, "
                          f"MEM={format_bytes(proc.get('memory', {}).get('rss', 0))}")
                print("  PASSED\n")
            else:
                print(f"  FAILED - {result.get('error')}\n")
                return 1

            # Test 3: Get cgroup metrics (may fail if no cgroups)
            print("--- Test 11.3: Cgroup Metrics ---")
            result = client.get_cgroup_metrics()

            # This may fail if not running sandboxed - that's OK
            if result.get("success"):
                metrics = result.get("metrics", {})
                cpu = metrics.get("cpu", {})
                mem = metrics.get("memory", {})
                pids = metrics.get("pids", {})
                print(f"  CPU Usage: {cpu.get('usage_usec', 0) / 1000000:.2f}s")
                print(f"  Memory: {format_bytes(mem.get('current', 0))} / {format_bytes(mem.get('max', 0))}")
                print(f"  PIDs: {pids.get('current', 0)} / {pids.get('max', 0)}")
                print("  PASSED\n")
            else:
                print(f"  Cgroup not available (expected if not sandboxed)")
                print("  PASSED (graceful handling)\n")

            # Test 4: Multiple system metrics calls (for rate calculation)
            print("--- Test 11.4: Metrics Stability ---")
            import time

            results = []
            for i in range(3):
                result = client.get_system_metrics()
                if result.get("success"):
                    results.append(result.get("metrics", {}))
                time.sleep(0.5)

            if len(results) == 3:
                cpu_readings = [r.get("cpu", {}).get("percent", 0) for r in results]
                print(f"  CPU readings: {[f'{c:.1f}%' for c in cpu_readings]}")
                print("  PASSED\n")
            else:
                print("  FAILED - Could not collect multiple readings\n")
                return 1

            print("=== Test 11 PASSED ===")
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
