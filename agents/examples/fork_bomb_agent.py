#!/usr/bin/env python3
"""
Fork Bomb Agent - Tests PID Limit Protection

This agent attempts to spawn unlimited processes via Python's multiprocessing.
When run in a sandboxed environment with max_pids limit, the kernel's cgroups
will prevent excessive process creation.

== Expected Behavior ==

Without sandboxing:  Creates many processes, potentially crashes system
With sandboxing:     Hits PID limit, fails to create more processes

== What This Demonstrates ==

AgentOS can protect against:
- Fork bomb attacks
- Runaway process spawning
- Resource exhaustion via process creation

This is a real security threat in multi-agent systems where untrusted
code might try to take over system resources.
"""

import os
import sys
import time
import signal
import multiprocessing

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOSClient

def child_process(n):
    """Child process that just sleeps"""
    try:
        # Register so we know the process started
        time.sleep(60)  # Sleep for a long time
    except:
        pass

def attempt_fork_bomb():
    """Attempt to create many processes"""
    processes = []
    created = 0
    failed = 0

    print("[FORK-BOMB] Starting process spawning attack...")
    print(f"[FORK-BOMB] Current PID: {os.getpid()}")

    # Try to spawn 100 processes
    for i in range(100):
        try:
            p = multiprocessing.Process(target=child_process, args=(i,))
            p.start()
            processes.append(p)
            created += 1

            if created % 10 == 0:
                print(f"[FORK-BOMB] Created {created} processes...")

        except OSError as e:
            failed += 1
            if failed == 1:
                print(f"[FORK-BOMB] Process creation BLOCKED: {e}")
            break
        except Exception as e:
            failed += 1
            if failed == 1:
                print(f"[FORK-BOMB] Process creation failed: {e}")
            break

    print(f"[FORK-BOMB] Results: {created} created, {failed} blocked")

    # Cleanup
    for p in processes:
        try:
            p.terminate()
            p.join(timeout=0.1)
        except:
            pass

    return created, failed

def main():
    print("=" * 60)
    print("  Fork Bomb Agent")
    print("  Testing PID limit protection")
    print("=" * 60)
    print()

    # Connect to kernel
    client = AgentOSClient()
    if client.connect():
        print("[FORK-BOMB] Connected to AgentOS kernel")

        # Register ourselves
        result = client.register_name("fork-bomb")
        if result.get("success"):
            print(f"[FORK-BOMB] Registered as 'fork-bomb' (id={result.get('agent_id')})")
    else:
        print("[FORK-BOMB] Running standalone (no kernel connection)")

    print()

    # Set multiprocessing start method
    try:
        multiprocessing.set_start_method('fork')
    except RuntimeError:
        pass  # Already set

    # Attempt the fork bomb
    created, failed = attempt_fork_bomb()

    print()
    if failed > 0:
        print("[FORK-BOMB] PROTECTION VERIFIED: PID limit prevented fork bomb")
        print("[FORK-BOMB] cgroups max_pids successfully limited process creation")
    else:
        print("[FORK-BOMB] WARNING: All processes created (no PID limit active)")
        print("[FORK-BOMB] Run with sandboxing enabled for protection")

    # Keep running briefly to be observable
    print()
    print("[FORK-BOMB] Agent exiting...")

    if client._sock:
        client.disconnect()

    return 0

if __name__ == '__main__':
    sys.exit(main())
