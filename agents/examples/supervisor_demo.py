#!/usr/bin/env python3
"""
Supervisor Demo - PID 1 Semantics for AI Agents

This demo shows how AgentOS enables systemd/init-style supervision
for AI agents.

== What This Demo Shows ==

1. AUTOMATIC RESTART
   - Unstable agents crash randomly
   - Supervisor detects crashes
   - Supervisor restarts failed agents

2. RESTART LIMITS
   - Each agent gets max 3 restart attempts
   - After that, agent is "escalated"
   - Escalated agents require manual intervention

3. BACKOFF
   - Restart delay increases with each attempt
   - Prevents restart storms

== Why This Matters ==

Production agent systems need:
- Recovery from unexpected crashes
- Protection against infinite restart loops
- Alerting for persistent failures

Python frameworks run agents as coroutines.
If one crashes, it often takes down others.
No true supervision is possible.

AgentOS runs agents as real OS processes.
True supervision is possible, just like systemd.

== Usage ==

  python3 supervisor_demo.py

  Or run the supervisor directly:
  python3 supervisor_agent.py

"""

import sys
import os
import time
import subprocess
import signal

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOSClient

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def print_header():
    """Print demo header"""
    print("=" * 70)
    print("  AgentOS Supervisor Demo")
    print("  PID 1 Semantics for AI Agents")
    print("=" * 70)
    print()
    print("  This demo shows systemd-style supervision for agents:")
    print("  - Automatic crash detection")
    print("  - Automatic restart with backoff")
    print("  - Restart limits and escalation")
    print()


def main():
    print_header()

    # Check if kernel is running
    print("Checking kernel connection...")
    client = AgentOSClient()
    if not client.connect():
        print("ERROR: Failed to connect to kernel")
        print("Make sure the kernel is running: ./build/agentos_kernel")
        return 1

    print("Kernel is running!")
    client.disconnect()
    print()

    print("-" * 70)
    print("  Running Supervisor Agent")
    print("-" * 70)
    print()
    print("The supervisor will:")
    print("  1. Spawn 3 unstable worker agents")
    print("  2. Workers will crash randomly after 3-8 heartbeats")
    print("  3. Supervisor will detect crashes and restart workers")
    print("  4. After 3 restarts, workers are 'escalated' (given up)")
    print("  5. Demo ends when all workers are escalated")
    print()
    print("Press Ctrl+C to stop early")
    print()
    print("-" * 70)
    print()

    # Run the supervisor agent
    supervisor_script = os.path.join(SCRIPT_DIR, "supervisor_agent.py")

    try:
        # Run supervisor as subprocess so we can see its output
        process = subprocess.Popen(
            ["python3", supervisor_script],
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        # Wait for it to complete
        process.wait()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        process.terminate()
        process.wait()

    # Summary
    print()
    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    print()
    print("  AgentOS enables OS-style supervision because:")
    print()
    print("  1. REAL PROCESSES")
    print("     Agents run as separate OS processes")
    print("     Crashes are detected via process exit")
    print()
    print("  2. LIFECYCLE MANAGEMENT")
    print("     Kernel tracks agent spawn/exit")
    print("     Supervisor can query agent status")
    print()
    print("  3. IPC FOR COORDINATION")
    print("     Agents communicate via kernel IPC")
    print("     Heartbeats, crash notifications, etc.")
    print()
    print("  Positioning: 'AgentOS is systemd for AI agents'")
    print()
    print("  This pattern enables:")
    print("    - High availability agent systems")
    print("    - Automatic recovery from crashes")
    print("    - Production-grade reliability")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
