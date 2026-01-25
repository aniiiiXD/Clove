#!/usr/bin/env python3
"""
CPU Hog Agent - Stress test for CPU throttling

This agent demonstrates kernel-level CPU isolation by:
1. Connecting to the kernel
2. Running an infinite CPU-bound loop
3. Getting throttled by cgroups cpu.max limit

Expected behavior (with root/cgroups):
- Agent gets CPU-throttled to configured quota
- Does NOT affect other agents
- Kernel can still kill/manage it

Without root: runs unthrottled until manually killed.
"""
 
import sys
import os
import time

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOSClient


def cpu_burn():
    """Pure CPU burn - no I/O, no sleep"""
    x = 0
    while True:
        # Busy computation
        x = (x * 1103515245 + 12345) & 0x7fffffff
        # Occasional status (every ~10M iterations)
        if x % 10000000 == 0:
            pass  # Just keep burning


def main():
    socket_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/clove.sock'

    print(f"[CPU-HOG] Starting - PID: {os.getpid()}")
    print(f"[CPU-HOG] Connecting to {socket_path}")

    client = AgentOSClient(socket_path)

    if not client.connect():
        print("[CPU-HOG] ERROR: Failed to connect")
        return 1

    # Announce ourselves
    response = client.echo(f"CPU-HOG agent started, PID={os.getpid()}")
    print(f"[CPU-HOG] Kernel acknowledged: {response}")

    print("[CPU-HOG] Starting infinite CPU burn loop...")
    print("[CPU-HOG] (Should be throttled by cgroups if running with root)")

    client.disconnect()

    # Start the infinite burn
    start = time.time()
    iterations = 0

    try:
        while True:
            # Busy computation
            x = 0
            for _ in range(1000000):
                x = (x * 1103515245 + 12345) & 0x7fffffff
            iterations += 1

            # Log every ~5 seconds worth of work
            elapsed = time.time() - start
            if iterations % 50 == 0:
                rate = iterations / elapsed if elapsed > 0 else 0
                print(f"[CPU-HOG] {elapsed:.1f}s - {iterations}M iterations ({rate:.1f}/s)")

    except KeyboardInterrupt:
        print(f"\n[CPU-HOG] Interrupted after {time.time() - start:.1f}s")

    return 0


if __name__ == '__main__':
    sys.exit(main())
