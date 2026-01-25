#!/usr/bin/env python3
"""
Echo Test Agent

Simple agent for testing deployment and connectivity.
Used to verify that the kernel is running and reachable.

Usage:
    agentos agent run agents/examples/echo_test.py --machine <machine_id>
"""

import sys
import os
import time

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOS


def main():
    agent = AgentOS("echo_test")

    agent.write("=" * 50)
    agent.write("AgentOS Echo Test Agent")
    agent.write("=" * 50)

    # Test basic write
    agent.write(f"Agent ID: {agent.agent_id}")
    agent.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Test environment info
    agent.write("\n--- Environment ---")
    agent.write(f"MACHINE_ID: {os.environ.get('MACHINE_ID', 'not set')}")
    agent.write(f"RELAY_URL: {os.environ.get('RELAY_URL', 'not set')}")

    # Test multiple writes
    agent.write("\n--- Echo Test ---")
    for i in range(5):
        agent.write(f"  Echo {i + 1}: Hello from AgentOS!")
        time.sleep(0.5)

    agent.write("\n--- Test Complete ---")
    agent.write("All systems operational!")

    agent.exit(0)


if __name__ == "__main__":
    main()
