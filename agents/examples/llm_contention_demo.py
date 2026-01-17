#!/usr/bin/env python3
"""
LLM Contention Demo - Fair Scheduling for Multiple Agents

This demo proves AgentOS provides fair LLM access when multiple
agents compete for the shared LLM resource.

== What This Demo Shows ==

1. FAIR SCHEDULING
   - Spawn 5 agents simultaneously
   - All agents request LLM at the same time
   - Kernel queues requests through single LLM subprocess
   - Each agent gets fair access

2. RESOURCE TRACKING
   - Track latency per agent
   - Track tokens used per agent
   - Compare wait times

3. NO STARVATION
   - Even with contention, all agents complete
   - No single agent monopolizes the LLM

== Why This Matters ==

In multi-agent systems, LLM access is a shared resource.
Without fair scheduling:
- Some agents might starve
- Latency becomes unpredictable
- System becomes unreliable

AgentOS uses a single LLM subprocess, naturally serializing
requests. This provides:
- Predictable ordering
- Fair access
- No starvation

== Usage ==

  # Make sure GEMINI_API_KEY is set
  export GEMINI_API_KEY=your_key_here

  # Run the demo
  python3 llm_contention_demo.py

"""

import sys
import os
import time
import json

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

# Demo configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NUM_AGENTS = 5
REQUESTS_PER_AGENT = 2
WAIT_TIMEOUT = 120  # seconds to wait for all agents to complete


def print_header():
    """Print demo header"""
    print("=" * 70)
    print("  AgentOS LLM Contention Demo")
    print("  Fair Scheduling for Multiple Agents")
    print("=" * 70)
    print()
    print(f"  Agents: {NUM_AGENTS}")
    print(f"  Requests per agent: {REQUESTS_PER_AGENT}")
    print(f"  Total LLM requests: {NUM_AGENTS * REQUESTS_PER_AGENT}")
    print()


def spawn_agents(client):
    """Spawn multiple agents simultaneously"""
    agents = {}
    script_path = os.path.join(SCRIPT_DIR, "llm_requester_agent.py")

    print("Spawning agents...")
    print()

    for i in range(NUM_AGENTS):
        name = f"llm-agent-{i+1}"

        result = client.spawn(
            name=name,
            script=script_path,
            sandboxed=False,  # Don't sandbox - need network for LLM
            network=True,
            limits={
                "memory": 256 * 1024 * 1024,
                "cpu_quota": 100000,
                "max_pids": 16
            }
        )

        if result and result.get('status') == 'running':
            agents[name] = {
                'id': result.get('id'),
                'pid': result.get('pid'),
                'status': 'running',
                'spawn_time': time.time()
            }
            print(f"  Spawned: {name} (PID={result.get('pid')})")
        else:
            print(f"  FAILED: {name} - {result}")

    return agents


def wait_for_completion(client, agents, timeout):
    """Wait for all agents to complete"""
    print()
    print(f"Waiting for agents to complete (timeout: {timeout}s)...")
    print()

    start_time = time.time()
    results = []

    while time.time() - start_time < timeout:
        # Check which agents are still running
        running_agents = client.list_agents()
        running_names = set()

        if isinstance(running_agents, list):
            for agent in running_agents:
                running_names.add(agent.get('name', ''))

        # Update agent status
        all_done = True
        for name, info in agents.items():
            if info['status'] == 'running':
                if name not in running_names:
                    info['status'] = 'completed'
                    info['end_time'] = time.time()
                    elapsed = info['end_time'] - info['spawn_time']
                    print(f"  {name} completed ({elapsed:.1f}s total)")
                else:
                    all_done = False

        if all_done:
            break

        # Check for messages from agents
        recv_result = client.recv(max_messages=10)
        if recv_result.get('success') and recv_result.get('count', 0) > 0:
            for msg in recv_result.get('messages', []):
                agent_name = msg.get('from_name', 'unknown')
                message = msg.get('message', {})
                if isinstance(message, dict) and 'avg_latency_ms' in message:
                    results.append(message)
                    print(f"  Received results from {agent_name}")

        time.sleep(1)

    return results


def print_results(results, agents):
    """Print formatted results table"""
    print()
    print("=" * 70)
    print("  Results")
    print("=" * 70)
    print()

    if not results:
        print("  No results received from agents")
        print()
        print("  This can happen if:")
        print("    - GEMINI_API_KEY is not set")
        print("    - Agents failed to connect to LLM")
        print("    - Network issues")
        return

    # Sort by agent name
    results.sort(key=lambda r: r.get('agent', ''))

    # Print table header
    print(f"  {'Agent':<15} {'Requests':<10} {'Success':<10} {'Avg Latency':<12} {'Tokens':<10}")
    print("  " + "-" * 60)

    total_requests = 0
    total_success = 0
    total_tokens = 0
    all_latencies = []

    for r in results:
        agent = r.get('agent', 'unknown')
        requests = r.get('requests', 0)
        success = r.get('successful', 0)
        avg_latency = r.get('avg_latency_ms', 0)
        tokens = r.get('total_tokens', 0)

        print(f"  {agent:<15} {requests:<10} {success:<10} {avg_latency:>8.0f}ms  {tokens:<10}")

        total_requests += requests
        total_success += success
        total_tokens += tokens
        all_latencies.append(avg_latency)

    print("  " + "-" * 60)

    avg_overall = sum(all_latencies) / len(all_latencies) if all_latencies else 0
    print(f"  {'TOTAL':<15} {total_requests:<10} {total_success:<10} {avg_overall:>8.0f}ms  {total_tokens:<10}")

    print()

    # Analysis
    if all_latencies:
        min_lat = min(all_latencies)
        max_lat = max(all_latencies)
        spread = max_lat - min_lat

        print("  Analysis:")
        print(f"    Min latency: {min_lat:.0f}ms")
        print(f"    Max latency: {max_lat:.0f}ms")
        print(f"    Spread: {spread:.0f}ms")
        print()

        if spread < avg_overall * 0.5:
            print("  FAIR SCHEDULING VERIFIED")
            print("    Latency spread is within acceptable range")
            print("    All agents received similar LLM access")
        else:
            print("  NOTE: High latency variance")
            print("    This may be due to network conditions or LLM load")


def main():
    print_header()

    # Check for API key
    if not os.environ.get('GEMINI_API_KEY') and not os.environ.get('GOOGLE_API_KEY'):
        print("WARNING: No GEMINI_API_KEY set")
        print("LLM requests will fail without an API key")
        print()

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

    # Spawn agents
    print("-" * 70)
    print("  Phase 1: Spawn Agents")
    print("-" * 70)
    print()

    agents = spawn_agents(client)

    if not agents:
        print("ERROR: No agents spawned")
        client.disconnect()
        return 1

    # Wait for agents and collect results
    print()
    print("-" * 70)
    print("  Phase 2: Wait for Completion")
    print("-" * 70)

    results = wait_for_completion(client, agents, WAIT_TIMEOUT)

    # Print results
    print_results(results, agents)

    # Cleanup any remaining agents
    print()
    print("Cleaning up...")
    for name in agents.keys():
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
    print("  AgentOS provides fair LLM scheduling by:")
    print()
    print("  1. SINGLE QUEUE")
    print("     All LLM requests go through one subprocess")
    print("     Natural FIFO ordering ensures fairness")
    print()
    print("  2. NO STARVATION")
    print("     Every agent's request is processed")
    print("     No agent can monopolize the LLM")
    print()
    print("  3. PREDICTABLE LATENCY")
    print("     Latency varies with queue depth")
    print("     Each agent experiences similar wait times")
    print()
    print("  Positioning: 'AgentOS is a kernel scheduler for LLM access'")
    print()

    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
