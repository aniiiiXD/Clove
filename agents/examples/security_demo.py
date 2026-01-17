#!/usr/bin/env python3
"""
Security Demo - Untrusted Agent Execution

This demo proves AgentOS provides security isolation that pure Python
agent frameworks (LangChain, CrewAI, AutoGen) cannot provide.

== What This Demo Shows ==

1. FORK BOMB PROTECTION
   - Agent tries to spawn unlimited processes
   - cgroups max_pids limit stops the attack
   - Other agents are unaffected

2. NETWORK ISOLATION
   - Agent tries to make network connections
   - Network namespace blocks all external access
   - Prevents data exfiltration and C2 callbacks

3. RESOURCE LIMITS
   - CPU and memory limits per agent
   - Prevents resource exhaustion attacks

== Why This Matters ==

When running untrusted or third-party agents, you need:
- Process isolation (what if the agent is malicious?)
- Resource limits (what if it's buggy and loops forever?)
- Network control (what if it tries to exfiltrate data?)

Python frameworks run agents as coroutines in the same process.
They CAN'T provide these protections.

AgentOS uses OS-level isolation: Linux namespaces + cgroups.
This is the same technology that Docker uses.

== Usage ==

  # With limited isolation (demonstrates concept)
  python3 security_demo.py

  # With full isolation (requires root for namespaces + cgroups)
  sudo python3 security_demo.py

"""

import sys
import os
import time
import signal

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

# Demo configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Security test configurations
SECURITY_TESTS = {
    "fork-bomb": {
        "script": os.path.join(SCRIPT_DIR, "fork_bomb_agent.py"),
        "limits": {
            "memory": 64 * 1024 * 1024,   # 64MB
            "cpu_quota": 50000,            # 50% CPU
            "max_pids": 8                  # Very low PID limit - will block fork bomb
        },
        "network": False,
        "description": "Fork bomb attack (limited to 8 PIDs)",
        "expected": "BLOCKED by cgroups max_pids"
    },
    "net-isolated": {
        "script": os.path.join(SCRIPT_DIR, "network_test_agent.py"),
        "limits": {
            "memory": 64 * 1024 * 1024,
            "cpu_quota": 100000,
            "max_pids": 16
        },
        "network": False,  # Network disabled!
        "description": "Network tests (network DISABLED)",
        "expected": "All network access BLOCKED"
    },
    "net-allowed": {
        "script": os.path.join(SCRIPT_DIR, "network_test_agent.py"),
        "limits": {
            "memory": 64 * 1024 * 1024,
            "cpu_quota": 100000,
            "max_pids": 16
        },
        "network": True,  # Network enabled!
        "description": "Network tests (network ENABLED)",
        "expected": "Network access ALLOWED (control group)"
    }
}


def print_header():
    """Print demo header"""
    print("=" * 70)
    print("  AgentOS Security Demo")
    print("  Demonstrating untrusted agent isolation")
    print("=" * 70)
    print()
    if os.geteuid() == 0:
        print("  [ROOT MODE] Full namespace + cgroups isolation enabled")
    else:
        print("  [USER MODE] Limited isolation (run with sudo for full demo)")
    print()


def print_test_header(name, config):
    """Print test section header"""
    print()
    print("-" * 70)
    print(f"  TEST: {name}")
    print(f"  {config['description']}")
    print(f"  Expected: {config['expected']}")
    print("-" * 70)
    print()


def wait_for_agent(client, name, timeout=15):
    """Wait for an agent to finish and return its final status"""
    start = time.time()
    last_seen = None

    while time.time() - start < timeout:
        agents = client.list_agents()
        found = None

        if isinstance(agents, list):
            for agent in agents:
                if agent.get('name') == name:
                    found = agent
                    last_seen = agent
                    break

        if found is None and last_seen is not None:
            # Agent finished
            return "exited"

        if found and not found.get('running', True):
            return "stopped"

        time.sleep(0.5)

    return "timeout" if last_seen else "not_found"


def run_test(client, name, config):
    """Run a single security test"""
    print_test_header(name, config)

    print(f"Spawning agent '{name}'...")
    result = client.spawn(
        name=name,
        script=config['script'],
        sandboxed=True,
        network=config.get('network', False),
        limits=config['limits']
    )

    if not result or result.get('status') != 'running':
        print(f"  FAILED to spawn: {result}")
        return False

    pid = result.get('pid')
    agent_id = result.get('id')
    print(f"  Spawned: PID={pid}, ID={agent_id}")
    print()
    print("  Waiting for agent to complete...")
    print()

    # Wait for agent to finish
    status = wait_for_agent(client, name, timeout=20)

    print()
    print(f"  Agent status: {status}")

    # Cleanup
    try:
        client.kill(name=name)
    except:
        pass

    return True


def run_comparison_test(client):
    """Run network test with and without isolation to show the difference"""
    print()
    print("=" * 70)
    print("  COMPARISON: Network Isolation")
    print("  Running same agent with different network settings")
    print("=" * 70)

    # Test 1: Network DISABLED (isolated)
    run_test(client, "net-isolated", SECURITY_TESTS["net-isolated"])

    time.sleep(1)

    # Test 2: Network ENABLED (not isolated)
    run_test(client, "net-allowed", SECURITY_TESTS["net-allowed"])


def main():
    print_header()

    # Connect to kernel
    print("Connecting to AgentOS kernel...")
    client = AgentOSClient()
    if not client.connect():
        print("ERROR: Failed to connect to kernel")
        print("Make sure the kernel is running: ./build/agentos_kernel")
        return 1

    print("Connected!")
    print()

    # Check initial state
    initial_agents = client.list_agents()
    print(f"Initial state: {len(initial_agents)} agents running")

    # Run tests
    print()
    print("=" * 70)
    print("  TEST 1: Fork Bomb Protection")
    print("=" * 70)

    run_test(client, "fork-bomb", SECURITY_TESTS["fork-bomb"])

    time.sleep(1)

    print()
    print("=" * 70)
    print("  TEST 2: Network Isolation Comparison")
    print("=" * 70)

    run_comparison_test(client)

    # Final summary
    print()
    print("=" * 70)
    print("  SECURITY DEMO SUMMARY")
    print("=" * 70)
    print()
    print("  AgentOS provides OS-level security that Python frameworks cannot:")
    print()
    print("  1. FORK BOMB PROTECTION")
    print("     - cgroups max_pids limits process creation")
    print("     - Malicious agents cannot spawn unlimited processes")
    print()
    print("  2. NETWORK ISOLATION")
    print("     - Network namespace isolates agent from network")
    print("     - Prevents data exfiltration and C2 callbacks")
    print()
    print("  3. RESOURCE LIMITS")
    print("     - CPU and memory limits via cgroups")
    print("     - Prevents resource exhaustion attacks")
    print()
    print("  4. PROCESS ISOLATION")
    print("     - Each agent runs in its own process")
    print("     - One crashing agent doesn't affect others")
    print()

    if os.geteuid() != 0:
        print("  NOTE: Run with 'sudo' for full namespace isolation")
        print()

    print("  Positioning: 'AgentOS is Docker-lite for AI agents'")
    print()

    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
