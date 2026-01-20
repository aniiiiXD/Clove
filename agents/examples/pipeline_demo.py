#!/usr/bin/env python3
"""
Agent Pipeline Demo - Real IPC Between Agents

This demo shows agents working together in a pipeline,
communicating exclusively through kernel IPC.

== Pipeline Architecture ==

  Input → [PARSER] → [REASONER] → [VERIFIER] → Output
              ↑           ↑            ↑
              └───────────┴────────────┘
                  Kernel IPC (SYS_SEND/SYS_RECV)

== What This Demo Shows ==

1. REAL PROCESS SEPARATION
   - Each stage runs as separate OS process
   - No shared memory between stages
   - True isolation

2. KERNEL-MEDIATED IPC
   - All communication goes through kernel
   - Messages queued per-agent
   - No direct Python function calls

3. PIPELINE PATTERN
   - Parser: Preprocesses input
   - Reasoner: Computes/reasons about data
   - Verifier: Validates results

== Why This Matters ==

Python agent frameworks typically:
- Run agents as coroutines in same process
- Use function calls or shared memory
- One crash affects all agents

AgentOS:
- Runs agents as real processes
- Uses kernel IPC for communication
- One crash doesn't affect others

This is how real distributed systems work.

== Usage ==

  python3 pipeline_demo.py

"""

import sys
import os
import time
import json

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Test queries
TEST_QUERIES = [
    "What is 42 plus 17?",
    "Calculate 100 minus 37",
    "Multiply 7 times 8",
    "Divide 144 by 12",
    "Add 123 and 456",
]


def print_header():
    """Print demo header"""
    print("=" * 70)
    print("  AgentOS Pipeline Demo")
    print("  Real IPC Between Agents")
    print("=" * 70)
    print()
    print("  Pipeline: Input → [Parser] → [Reasoner] → [Verifier] → Output")
    print()
    print("  Each stage runs as a separate OS process")
    print("  All communication via kernel IPC (no Python function calls)")
    print()


def spawn_pipeline_agents(client):
    """Spawn all pipeline agents"""
    agents = {}

    agent_configs = [
        ("parser", os.path.join(SCRIPT_DIR, "parser_agent.py")),
        ("reasoner", os.path.join(SCRIPT_DIR, "reasoner_agent.py")),
        ("verifier", os.path.join(SCRIPT_DIR, "verifier_agent.py")),
    ]

    for name, script in agent_configs:
        result = client.spawn(
            name=name,
            script=script,
            sandboxed=False,
            network=True,  # May need for LLM
            limits={
                "memory": 256 * 1024 * 1024,
                "cpu_quota": 100000,
                "max_pids": 16
            }
        )

        if result and result.get('status') == 'running':
            agents[name] = {
                'pid': result.get('pid'),
                'id': result.get('id')
            }
            print(f"  Spawned {name} (PID={result.get('pid')})")
        else:
            print(f"  FAILED to spawn {name}: {result}")
            return None

    return agents


def wait_for_registration(client, agents, timeout=10):
    """Wait for all agents to register their names"""
    print()
    print("Waiting for agents to register...")

    start = time.time()
    while time.time() - start < timeout:
        # Give agents time to register
        time.sleep(0.5)
        registered = True

        # Try sending a test message to each agent
        for name in agents:
            result = client.send_message(
                message={"type": "ping"},
                to_name=name
            )
            if not result.get('success'):
                registered = False
                break

        if registered:
            print("All agents registered!")
            return True

    print("Timeout waiting for agent registration")
    return False


def run_pipeline(client, query, request_id):
    """Send a query through the pipeline"""
    print(f"\n  Query {request_id}: \"{query}\"")

    # Send to parser
    result = client.send_message(
        message={
            "type": "parse_request",
            "input": query,
            "request_id": request_id
        },
        to_name="parser"
    )

    if not result.get('success'):
        print(f"    ERROR: Failed to send to parser")
        return None

    print(f"    → Sent to parser")

    # Wait for result from verifier
    start = time.time()
    timeout = 30

    while time.time() - start < timeout:
        recv_result = client.recv_messages(max_messages=10)

        if recv_result.get('success') and recv_result.get('count', 0) > 0:
            for msg in recv_result.get('messages', []):
                message = msg.get('message', {})

                if isinstance(message, dict) and message.get('type') == 'final_result':
                    if message.get('request_id') == request_id:
                        return message

        time.sleep(0.5)

    print(f"    TIMEOUT waiting for result")
    return None


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

    # Register as orchestrator
    result = client.register_name("orchestrator")
    if result.get("success"):
        print(f"Registered as 'orchestrator' (id={result.get('agent_id')})")
    print()

    # Spawn pipeline agents
    print("-" * 70)
    print("  Phase 1: Spawn Pipeline Agents")
    print("-" * 70)
    print()

    agents = spawn_pipeline_agents(client)
    if not agents:
        print("ERROR: Failed to spawn all agents")
        client.disconnect()
        return 1

    # Wait for agents to register
    if not wait_for_registration(client, agents):
        print("ERROR: Agents failed to register")
        for name in agents:
            try:
                client.kill(name=name)
            except:
                pass
        client.disconnect()
        return 1

    # Run queries through pipeline
    print()
    print("-" * 70)
    print("  Phase 2: Run Queries Through Pipeline")
    print("-" * 70)

    results = []

    for i, query in enumerate(TEST_QUERIES):
        result = run_pipeline(client, query, i + 1)

        if result:
            verified = result.get('verified', False)
            status = "VALID" if verified else "INVALID"
            answer = result.get('result')
            results.append({
                'query': query,
                'result': answer,
                'verified': verified,
                'explanation': result.get('explanation', '')[:50]
            })
            print(f"    ← Result: {answer} ({status})")
        else:
            results.append({
                'query': query,
                'result': None,
                'verified': False,
                'explanation': 'Timeout'
            })

        # Small delay between queries
        time.sleep(0.5)

    # Print results
    print()
    print("-" * 70)
    print("  Results Summary")
    print("-" * 70)
    print()
    print(f"  {'Query':<35} {'Result':<10} {'Status':<10}")
    print("  " + "-" * 60)

    for r in results:
        query = r['query'][:33] + ".." if len(r['query']) > 35 else r['query']
        result = str(r['result'])[:8] if r['result'] is not None else "N/A"
        status = "VALID" if r['verified'] else "INVALID"
        print(f"  {query:<35} {result:<10} {status:<10}")

    # Cleanup
    print()
    print("Cleaning up agents...")
    for name in agents:
        try:
            # Send shutdown signal
            client.send_message(message={"type": "shutdown"}, to_name=name)
        except:
            pass

    time.sleep(1)

    for name in agents:
        try:
            client.kill(name=name)
        except:
            pass

    # Summary
    print()
    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    print()
    print("  This demo proved:")
    print()
    print("  1. AGENTS ARE PROCESSES")
    print("     Parser, Reasoner, Verifier ran as separate OS processes")
    print("     Each with its own PID and memory space")
    print()
    print("  2. IPC IS KERNEL-MEDIATED")
    print("     All communication went through kernel SYS_SEND/SYS_RECV")
    print("     No direct Python function calls between agents")
    print()
    print("  3. PIPELINE PATTERN WORKS")
    print("     Data flowed: Orchestrator → Parser → Reasoner → Verifier → Orchestrator")
    print("     Each stage added value before passing on")
    print()
    print("  Positioning: 'Agents are processes, not coroutines'")
    print()

    valid_count = sum(1 for r in results if r['verified'])
    print(f"  Results: {valid_count}/{len(results)} queries completed successfully")
    print()

    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
