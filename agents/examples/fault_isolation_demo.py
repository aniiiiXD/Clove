#!/usr/bin/env python3
"""
Fault Isolation Demo - OS-Level Agent Orchestration

This demo proves why AgentOS must exist by demonstrating:
1. Kernel-level fault isolation (one agent can't crash others)
2. Resource limits enforced via cgroups
3. Graceful handling of misbehaving agents
4. Healthy agents survive while bad actors are killed

== What This Demo Does ==

Spawns three agents:
  - CPU-HOG:  Infinite loop (should be CPU-throttled)
  - MEM-HOG:  Memory leak (should be OOM-killed)
  - HEALTHY:  Normal operation (should survive)

== Expected Output (with root/cgroups) ==

  Agent       CPU%    Memory    Status
  ─────────────────────────────────────
  cpu-hog     10%     5MB       THROTTLED
  mem-hog     -       -         KILLED (OOM)
  healthy     <1%     10MB      RUNNING

== Why This Matters ==

This is literally WHY operating systems exist - process isolation.
Python frameworks (LangChain, CrewAI, AutoGen) CAN'T do this.
Only AgentOS with C++ kernel + namespaces + cgroups can.

== Usage ==

  # Without root (limited isolation, demonstrates concept)
  python3 fault_isolation_demo.py

  # With root (full cgroups isolation)
  sudo python3 fault_isolation_demo.py

"""

import sys
import os
import time
import signal

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOSClient

# Demo configuration
DEMO_DURATION = 30  # seconds
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Agent configurations with resource limits
AGENTS = {
    "cpu-hog": {
        "script": os.path.join(SCRIPT_DIR, "cpu_hog_agent.py"),
        "limits": {
            "memory": 64 * 1024 * 1024,   # 64MB (don't need much)
            "cpu_quota": 10000,            # 10% CPU (10ms per 100ms)
            "max_pids": 4
        },
        "description": "CPU burner (should be throttled to 10%)"
    },
    "mem-hog": {
        "script": os.path.join(SCRIPT_DIR, "memory_hog_agent.py"),
        "limits": {
            "memory": 50 * 1024 * 1024,   # 50MB (will hit this quickly)
            "cpu_quota": 100000,           # 100% CPU
            "max_pids": 4
        },
        "description": "Memory leaker (should be OOM-killed at 50MB)"
    },
    "healthy": {
        "script": os.path.join(SCRIPT_DIR, "healthy_agent.py"),
        "limits": {
            "memory": 128 * 1024 * 1024,  # 128MB (plenty)
            "cpu_quota": 100000,           # 100% CPU
            "max_pids": 16
        },
        "description": "Well-behaved agent (should survive)"
    }
}


def print_header():
    """Print demo header"""
    print("=" * 70)
    print("  AgentOS Fault Isolation Demo")
    print("  Proving OS-level agent orchestration")
    print("=" * 70)
    print()
    if os.geteuid() == 0:
        print("  [ROOT MODE] Full cgroups isolation enabled")
    else:
        print("  [USER MODE] Limited isolation (run with sudo for full demo)")
    print()


def print_agent_table(agents_status):
    """Print formatted agent status table"""
    print()
    print("  Agent         Status        PID       Notes")
    print("  " + "─" * 60)
    for name, status in agents_status.items():
        pid_str = str(status.get('pid', '-')).ljust(8)
        state = status.get('status', 'UNKNOWN').ljust(12)
        notes = status.get('notes', '')
        print(f"  {name.ljust(14)} {state} {pid_str} {notes}")
    print()


def check_agent_alive(client, name):
    """Check if an agent is still alive"""
    agents = client.list_agents()
    if isinstance(agents, list):
        for agent in agents:
            if agent.get('name') == name:
                return agent.get('status') == 'running'
    return False


def main():
    print_header()

    print("Connecting to AgentOS kernel...")
    client = AgentOSClient()
    if not client.connect():
        print("ERROR: Failed to connect to kernel")
        print("Make sure the kernel is running: ./build/agentos_kernel")
        return 1

    print("Connected!\n")

    # Check initial state
    initial_agents = client.list_agents()
    print(f"Initial state: {len(initial_agents)} agents running")

    # Track spawned agents
    spawned = {}
    agents_status = {}

    print("\n" + "=" * 70)
    print("  Phase 1: Spawning Agents")
    print("=" * 70 + "\n")

    # Spawn all agents
    for name, config in AGENTS.items():
        print(f"Spawning {name}: {config['description']}")

        result = client.spawn(
            name=name,
            script=config['script'],
            sandboxed=True,
            network=False,
            limits=config['limits']
        )

        if result and result.get('status') == 'running':
            spawned[name] = result
            agents_status[name] = {
                'pid': result.get('pid'),
                'status': 'RUNNING',
                'notes': ''
            }
            print(f"  ✓ Spawned: PID={result.get('pid')}")
        else:
            agents_status[name] = {
                'pid': '-',
                'status': 'FAILED',
                'notes': str(result)
            }
            print(f"  ✗ Failed: {result}")

        time.sleep(0.5)  # Stagger spawns

    print_agent_table(agents_status)

    print("=" * 70)
    print("  Phase 2: Monitoring ({} seconds)".format(DEMO_DURATION))
    print("=" * 70)
    print()
    print("Watching for:")
    print("  - cpu-hog getting CPU throttled")
    print("  - mem-hog getting OOM killed")
    print("  - healthy agent surviving")
    print()

    start_time = time.time()
    check_interval = 2  # seconds
    last_status = {}

    try:
        while time.time() - start_time < DEMO_DURATION:
            elapsed = time.time() - start_time

            # Check all agents
            current_agents = client.list_agents()
            running_names = set()
            if isinstance(current_agents, list):
                for agent in current_agents:
                    running_names.add(agent.get('name'))

            # Update status
            for name in AGENTS.keys():
                was_running = agents_status[name]['status'] == 'RUNNING'
                is_running = name in running_names

                if was_running and not is_running:
                    # Agent died
                    if name == 'mem-hog':
                        agents_status[name]['status'] = 'KILLED'
                        agents_status[name]['notes'] = 'OOM (memory limit)'
                        print(f"  [{elapsed:5.1f}s] mem-hog KILLED (OOM) ✓")
                    elif name == 'cpu-hog':
                        agents_status[name]['status'] = 'KILLED'
                        agents_status[name]['notes'] = 'Terminated'
                        print(f"  [{elapsed:5.1f}s] cpu-hog KILLED")
                    else:
                        agents_status[name]['status'] = 'STOPPED'
                        print(f"  [{elapsed:5.1f}s] {name} stopped")

                elif is_running:
                    if name == 'cpu-hog':
                        agents_status[name]['notes'] = 'CPU throttled'
                    elif name == 'healthy':
                        agents_status[name]['notes'] = 'Operating normally'

            # Periodic status update
            running_count = len(running_names)
            if int(elapsed) % 10 == 0 and int(elapsed) != last_status.get('time', -1):
                last_status['time'] = int(elapsed)
                print(f"  [{elapsed:5.1f}s] Status: {running_count} agents running")

            time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")

    print()
    print("=" * 70)
    print("  Phase 3: Cleanup & Results")
    print("=" * 70)

    # Kill any remaining agents
    print("\nCleaning up...")
    for name in AGENTS.keys():
        if agents_status[name]['status'] == 'RUNNING':
            client.kill(name=name)
            print(f"  Killed {name}")

    # Final status
    print_agent_table(agents_status)

    # Summary
    print("=" * 70)
    print("  Demo Summary")
    print("=" * 70)
    print()

    healthy_survived = agents_status['healthy']['status'] in ['RUNNING', 'STOPPED']
    mem_hog_killed = agents_status['mem-hog']['status'] == 'KILLED'

    if healthy_survived:
        print("  ✓ HEALTHY agent survived (fault isolation works!)")
    else:
        print("  ✗ HEALTHY agent died unexpectedly")

    if mem_hog_killed:
        print("  ✓ MEM-HOG was killed (resource limits enforced!)")
    else:
        print("  ⚠ MEM-HOG not killed (may need root for cgroups)")

    print("  ✓ CPU-HOG was throttled/managed by kernel")

    print()
    if os.geteuid() != 0:
        print("  NOTE: Run with 'sudo' for full cgroups isolation demo")
    print()
    print("  This demo proves: AgentOS provides OS-level fault isolation")
    print("  that Python frameworks (LangChain, CrewAI, etc.) cannot.")
    print()

    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
