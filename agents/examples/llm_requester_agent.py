#!/usr/bin/env python3
"""
LLM Requester Agent - Used for LLM Contention Demo

This agent makes LLM requests and reports timing information.
Used by llm_contention_demo.py to demonstrate fair scheduling.
"""

import os
import sys
import time
import json
import random

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

def main():
    # Get agent name from environment or generate one
    agent_name = os.environ.get('AGENT_NAME', f'requester-{os.getpid()}')
    request_count = int(os.environ.get('REQUEST_COUNT', '3'))

    print(f"[{agent_name}] Starting LLM requester agent")
    print(f"[{agent_name}] Will make {request_count} LLM requests")

    # Connect to kernel
    client = AgentOSClient()
    if not client.connect():
        print(f"[{agent_name}] ERROR: Failed to connect to kernel")
        return 1

    print(f"[{agent_name}] Connected to AgentOS kernel")

    # Register ourselves
    result = client.register_name(agent_name)
    if result.get("success"):
        agent_id = result.get('agent_id')
        print(f"[{agent_name}] Registered (id={agent_id})")

    # Make LLM requests and track timing
    results = []

    for i in range(request_count):
        prompt = f"Agent {agent_name} request {i+1}: What is {random.randint(1, 100)} + {random.randint(1, 100)}? Answer briefly."

        print(f"[{agent_name}] Request {i+1}/{request_count} - sending...")

        start_time = time.time()
        response = client.think(prompt, thinking_level="low")
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        success = response.get('success', False)
        tokens = response.get('tokens', 0)

        results.append({
            'request_num': i + 1,
            'latency_ms': round(latency_ms, 1),
            'success': success,
            'tokens': tokens
        })

        status = "OK" if success else "FAIL"
        print(f"[{agent_name}] Request {i+1}/{request_count} - {status} in {latency_ms:.0f}ms ({tokens} tokens)")

        # Small delay between requests
        time.sleep(0.1)

    # Report summary
    total_time = sum(r['latency_ms'] for r in results)
    avg_latency = total_time / len(results) if results else 0
    total_tokens = sum(r['tokens'] for r in results)
    success_count = sum(1 for r in results if r['success'])

    print()
    print(f"[{agent_name}] === Summary ===")
    print(f"[{agent_name}] Requests: {success_count}/{request_count} successful")
    print(f"[{agent_name}] Total time: {total_time:.0f}ms")
    print(f"[{agent_name}] Avg latency: {avg_latency:.0f}ms")
    print(f"[{agent_name}] Total tokens: {total_tokens}")

    # Send results to orchestrator via IPC
    summary = {
        'agent': agent_name,
        'requests': request_count,
        'successful': success_count,
        'total_time_ms': round(total_time, 1),
        'avg_latency_ms': round(avg_latency, 1),
        'total_tokens': total_tokens,
        'results': results
    }

    # Try to send to orchestrator
    send_result = client.send_message(message=summary, to_name="orchestrator")
    if send_result.get('success'):
        print(f"[{agent_name}] Results sent to orchestrator")

    print(f"[{agent_name}] Agent complete")
    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
