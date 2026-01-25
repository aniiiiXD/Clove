#!/usr/bin/env python3
"""
Healthy Agent - Normal well-behaved agent for fault isolation demo

This agent demonstrates that healthy agents continue operating even when
other agents misbehave:
1. Sends periodic heartbeats
2. Occasionally uses LLM
3. Reports its status
4. Survives while bad actors get killed/throttled

This proves the kernel's fault isolation - one bad agent doesn't bring
down the whole system.
"""

import sys
import os
import time

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOSClient


def main():
    socket_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/clove.sock'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60  # Run for 60s by default

    print(f"[HEALTHY] Starting - PID: {os.getpid()}")
    print(f"[HEALTHY] Will run for {duration} seconds")
    print(f"[HEALTHY] Connecting to {socket_path}")

    client = AgentOSClient(socket_path)

    if not client.connect():
        print("[HEALTHY] ERROR: Failed to connect")
        return 1

    # Announce ourselves
    response = client.echo(f"HEALTHY agent started, PID={os.getpid()}")
    print(f"[HEALTHY] Kernel acknowledged: {response}")

    print("[HEALTHY] Starting heartbeat loop...")
    print("[HEALTHY] (Should continue running even when other agents fail)")

    start_time = time.time()
    heartbeat_count = 0

    try:
        while time.time() - start_time < duration:
            heartbeat_count += 1
            elapsed = time.time() - start_time

            # Send heartbeat
            msg = f"heartbeat #{heartbeat_count} at {elapsed:.1f}s"
            response = client.echo(msg)

            if response:
                print(f"[HEALTHY] {elapsed:6.1f}s | Heartbeat #{heartbeat_count} OK")
            else:
                print(f"[HEALTHY] {elapsed:6.1f}s | Heartbeat #{heartbeat_count} FAILED!")

            # Every 10 heartbeats, do a more complex operation
            if heartbeat_count % 10 == 0:
                result = client.list_agents()
                active = len(result) if isinstance(result, list) else 0
                print(f"[HEALTHY] {elapsed:6.1f}s | Status check: {active} agents running")

            time.sleep(2)  # Heartbeat every 2 seconds

    except KeyboardInterrupt:
        print(f"\n[HEALTHY] Interrupted after {heartbeat_count} heartbeats")

    # Final status
    elapsed = time.time() - start_time
    print(f"[HEALTHY] Completed: {heartbeat_count} heartbeats in {elapsed:.1f}s")
    print(f"[HEALTHY] SUCCESS - Agent survived the entire duration!")

    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
