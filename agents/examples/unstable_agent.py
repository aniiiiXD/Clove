#!/usr/bin/env python3
"""
Unstable Agent - Randomly Crashes for Supervisor Demo

This agent deliberately crashes after a random number of iterations
to test the supervisor's restart capability.
"""

import os
import sys
import time
import random

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOSClient

def main():
    agent_name = os.environ.get('AGENT_NAME', f'unstable-{os.getpid()}')
    crash_after = int(os.environ.get('CRASH_AFTER', str(random.randint(3, 8))))

    print(f"[{agent_name}] Starting (will crash after {crash_after} iterations)")

    # Connect to kernel
    client = AgentOSClient()
    if client.connect():
        result = client.register_name(agent_name)
        if result.get("success"):
            print(f"[{agent_name}] Registered (id={result.get('agent_id')})")

    iteration = 0
    while True:
        iteration += 1
        print(f"[{agent_name}] Heartbeat {iteration}/{crash_after}")

        # Send heartbeat to supervisor
        if client._sock:
            client.send_message(
                message={"type": "heartbeat", "iteration": iteration, "agent": agent_name},
                to_name="supervisor"
            )

        if iteration >= crash_after:
            print(f"[{agent_name}] CRASHING NOW!")
            # Simulate crash
            if client._sock:
                client.send_message(
                    message={"type": "crash", "agent": agent_name},
                    to_name="supervisor"
                )
            sys.exit(1)  # Non-zero exit = crash

        time.sleep(1)

    return 0


if __name__ == '__main__':
    sys.exit(main())
