#!/usr/bin/env python3
"""
Reasoner Agent - Stage 2 of Agent Pipeline

This agent receives parsed data from parser,
performs LLM reasoning, and passes result to verifier.
"""

import os
import sys
import time
import json

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient


def compute_result(parsed_data):
    """Compute the mathematical result from parsed data"""
    numbers = parsed_data.get('numbers', [])
    operation = parsed_data.get('operation')

    if len(numbers) < 2:
        return None, "Need at least 2 numbers"

    a, b = numbers[0], numbers[1]

    if operation == 'add':
        return a + b, f"{a} + {b} = {a + b}"
    elif operation == 'subtract':
        return a - b, f"{a} - {b} = {a - b}"
    elif operation == 'multiply':
        return a * b, f"{a} * {b} = {a * b}"
    elif operation == 'divide':
        if b == 0:
            return None, "Division by zero"
        return a / b, f"{a} / {b} = {a / b}"
    else:
        return None, "Unknown operation"


def main():
    print("[REASONER] Starting reasoner agent")

    # Connect to kernel
    client = AgentOSClient()
    if not client.connect():
        print("[REASONER] ERROR: Failed to connect to kernel")
        return 1

    # Register
    result = client.register_name("reasoner")
    if result.get("success"):
        print(f"[REASONER] Registered (id={result.get('agent_id')})")

    print("[REASONER] Waiting for parsed data from parser...")

    # Wait for messages
    processed = 0
    while processed < 5:
        # Check for messages
        recv_result = client.recv_messages(max_messages=1)

        if recv_result.get('success') and recv_result.get('count', 0) > 0:
            for msg in recv_result.get('messages', []):
                message = msg.get('message', {})

                if isinstance(message, dict) and message.get('type') == 'parsed_data':
                    request_id = message.get('request_id', 0)

                    print(f"[REASONER] Received parsed data: {message.get('numbers')} {message.get('operation')}")

                    # Compute result
                    result_value, explanation = compute_result(message)

                    # Optionally use LLM for more complex reasoning
                    use_llm = os.environ.get('USE_LLM', '').lower() == 'true'

                    if use_llm and result_value is not None:
                        print("[REASONER] Enhancing with LLM...")
                        llm_result = client.think(
                            f"Explain briefly: {explanation}",
                            thinking_level="low"
                        )
                        if llm_result.get('success'):
                            explanation = llm_result.get('content', explanation)

                    # Build result
                    reasoned = {
                        'type': 'reasoned_result',
                        'request_id': request_id,
                        'original': message.get('original', ''),
                        'numbers': message.get('numbers', []),
                        'operation': message.get('operation'),
                        'result': result_value,
                        'explanation': explanation,
                        'reasoned_at': time.time()
                    }

                    print(f"[REASONER] Result: {result_value} ({explanation[:50]}...)")

                    # Send to verifier
                    send_result = client.send_message(
                        message=reasoned,
                        to_name="verifier"
                    )

                    if send_result.get('success'):
                        print(f"[REASONER] Sent to verifier")
                        processed += 1
                    else:
                        print(f"[REASONER] Failed to send: {send_result}")

                elif isinstance(message, dict) and message.get('type') == 'shutdown':
                    print("[REASONER] Received shutdown signal")
                    break

        time.sleep(0.5)

    print(f"[REASONER] Processed {processed} messages, exiting")
    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
