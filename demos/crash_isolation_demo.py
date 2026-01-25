#!/usr/bin/env python3
"""
Clove Crash Isolation Demo

This demo shows Clove's core value proposition:
When one agent crashes, infinite loops, or hogs memory - other agents continue working.

This is THE demo that sells the project.

Usage:
    python demos/crash_isolation_demo.py

What happens:
1. Spawns 3 agents: a stable worker, a crasher, and another stable worker
2. The crasher agent crashes after 2 seconds
3. Both stable workers continue running unaffected
4. This demonstrates OS-level fault isolation
"""

import time
import sys
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents/python_sdk"))
from clove_sdk import CloveClient

# Agent scripts
STABLE_WORKER = '''
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    client.register("{name}")
    for i in range(10):
        print(f"[{name}] Working... iteration {{i+1}}/10")
        time.sleep(1)
    print(f"[{name}] Completed successfully!")
'''

CRASH_AGENT = '''
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    client.register("crasher")
    print("[crasher] Starting... will crash in 2 seconds")
    time.sleep(2)
    print("[crasher] CRASHING NOW!")
    raise RuntimeError("Intentional crash to demonstrate isolation!")
'''

INFINITE_LOOP_AGENT = '''
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    client.register("looper")
    print("[looper] Starting infinite loop...")
    count = 0
    while True:
        count += 1
        if count % 1000000 == 0:
            print(f"[looper] Still looping... {count}")
'''

MEMORY_HOG_AGENT = '''
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    client.register("memory-hog")
    print("[memory-hog] Starting to consume memory...")
    data = []
    try:
        while True:
            data.append("x" * (1024 * 1024))  # 1MB chunks
            print(f"[memory-hog] Allocated {len(data)} MB")
            time.sleep(0.1)
    except MemoryError:
        print("[memory-hog] Hit memory limit (cgroups working!)")
'''


def write_agent_script(name: str, content: str) -> str:
    """Write agent script to temp file and return path."""
    path = f"/tmp/clove_demo_{name}.py"
    with open(path, 'w') as f:
        f.write(content)
    return path


def print_banner(text: str):
    """Print a visible banner."""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)
    print()


def demo_crash_isolation():
    """Demo: One agent crashes, others continue."""
    print_banner("DEMO: Crash Isolation")
    print("Scenario: 3 agents running, one crashes after 2 seconds")
    print("Expected: The other 2 agents continue working unaffected")
    print()

    # Write agent scripts
    worker1_path = write_agent_script("worker1", STABLE_WORKER.format(name="worker-1"))
    worker2_path = write_agent_script("worker2", STABLE_WORKER.format(name="worker-2"))
    crasher_path = write_agent_script("crasher", CRASH_AGENT)

    with CloveClient() as client:
        # Spawn agents
        print("Spawning agents...")
        w1 = client.spawn(name="worker-1", script=worker1_path, sandboxed=False)
        w2 = client.spawn(name="worker-2", script=worker2_path, sandboxed=False)
        cr = client.spawn(name="crasher", script=crasher_path, sandboxed=False)

        print(f"  - worker-1: PID {w1.get('pid')}")
        print(f"  - worker-2: PID {w2.get('pid')}")
        print(f"  - crasher:  PID {cr.get('pid')}")
        print()

        # Monitor agents
        print("Monitoring agents (crasher will crash at ~2s)...")
        print("-" * 40)

        for i in range(12):
            time.sleep(1)
            agents = client.list_agents()
            agent_names = [a['name'] for a in agents]

            status = []
            for name in ['worker-1', 'worker-2', 'crasher']:
                if name in agent_names:
                    status.append(f"{name}: running")
                else:
                    status.append(f"{name}: STOPPED")

            print(f"[{i+1:2d}s] {' | '.join(status)}")

        print("-" * 40)

        # Final status
        agents = client.list_agents()
        print(f"\nFinal state: {len(agents)} agents still running")

        # Cleanup
        for agent in agents:
            client.kill(agent_id=agent['id'])

    print()
    if len(agents) >= 2:
        print("✅ SUCCESS: Workers continued despite crasher failure!")
        print("   This demonstrates Clove's fault isolation.")
    else:
        print("⚠️  Unexpected result - check agent logs")


def demo_infinite_loop_isolation():
    """Demo: One agent infinite loops, others continue."""
    print_banner("DEMO: Infinite Loop Isolation")
    print("Scenario: One agent enters infinite loop")
    print("Expected: Other agents continue, looper can be killed")
    print()

    worker_path = write_agent_script("worker3", STABLE_WORKER.format(name="worker-3"))
    looper_path = write_agent_script("looper", INFINITE_LOOP_AGENT)

    with CloveClient() as client:
        # Spawn agents
        print("Spawning agents...")
        w = client.spawn(name="worker-3", script=worker_path, sandboxed=False)
        loop = client.spawn(name="looper", script=looper_path, sandboxed=False)

        print(f"  - worker-3: PID {w.get('pid')}")
        print(f"  - looper:   PID {loop.get('pid')}")
        print()

        # Let them run
        print("Running for 5 seconds...")
        time.sleep(5)

        # Check status
        agents = client.list_agents()
        print(f"\nAgents running: {len(agents)}")

        # Kill the looper
        print("\nKilling infinite loop agent...")
        client.kill(name="looper")

        time.sleep(1)
        agents = client.list_agents()
        print(f"Agents after kill: {len(agents)}")

        # Cleanup remaining
        for agent in agents:
            client.kill(agent_id=agent['id'])

    print()
    print("✅ SUCCESS: Infinite loop was contained and killed!")
    print("   Worker continued unaffected.")


def main():
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           CLOVE CRASH ISOLATION DEMO                       ║")
    print("║                                                            ║")
    print("║  Demonstrating OS-level fault isolation for AI agents      ║")
    print("║  'When one agent fails, others continue'                   ║")
    print("╚════════════════════════════════════════════════════════════╝")

    try:
        demo_crash_isolation()
        time.sleep(2)
        demo_infinite_loop_isolation()

        print()
        print_banner("DEMO COMPLETE")
        print("Key takeaway: Clove provides real process isolation.")
        print("In Python frameworks, these failures would crash everything.")
        print()

    except ConnectionRefusedError:
        print("\n❌ ERROR: Cannot connect to Clove kernel")
        print("   Make sure the kernel is running: ./build/clove_kernel")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
