#!/usr/bin/env python3
"""
Verifier Agent - Stage 3 of Agent Pipeline

This agent receives reasoned results, verifies them,
and sends final results back to orchestrator.
"""

import os
import sys
import time
import json

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient


def verify_result(data):
    """Verify the mathematical result is correct"""
    numbers = data.get('numbers', [])
    operation = data.get('operation')
    result = data.get('result')

    if result is None or len(numbers) < 2:
        return False, "Invalid input"

    a, b = numbers[0], numbers[1]
    expected = None

    if operation == 'add':
        expected = a + b
    elif operation == 'subtract':
        expected = a - b
    elif operation == 'multiply':
        expected = a * b
    elif operation == 'divide':
        if b != 0:
            expected = a / b

    if expected is None:
        return False, "Could not compute expected result"

    # Allow small floating point differences
    if abs(result - expected) < 0.0001:
        return True, "Result verified correct"
    else:
        return False, f"Expected {expected}, got {result}"


def main():
    print("[VERIFIER] Starting verifier agent")

    # Connect to kernel
    client = AgentOSClient()
    if not client.connect():
        print("[VERIFIER] ERROR: Failed to connect to kernel")
        return 1

    # Register
    result = client.register_name("verifier")
    if result.get("success"):
        print(f"[VERIFIER] Registered (id={result.get('agent_id')})")

    print("[VERIFIER] Waiting for results from reasoner...")

    # Wait for messages
    processed = 0
    while processed < 5:
        # Check for messages
        recv_result = client.recv_messages(max_messages=1)

        if recv_result.get('success') and recv_result.get('count', 0) > 0:
            for msg in recv_result.get('messages', []):
                message = msg.get('message', {})

                if isinstance(message, dict) and message.get('type') == 'reasoned_result':
                    request_id = message.get('request_id', 0)
                    result_value = message.get('result')

                    print(f"[VERIFIER] Received result: {result_value}")

                    # Verify the result
                    verified, verification_msg = verify_result(message)

                    status = "VALID" if verified else "INVALID"
                    print(f"[VERIFIER] Verification: {status} - {verification_msg}")

                    # Build final result
                    final_result = {
                        'type': 'final_result',
                        'request_id': request_id,
                        'original_query': message.get('original', ''),
                        'result': result_value,
                        'explanation': message.get('explanation', ''),
                        'verified': verified,
                        'verification_message': verification_msg,
                        'pipeline_stages': ['parser', 'reasoner', 'verifier'],
                        'completed_at': time.time()
                    }

                    # Send to orchestrator
                    send_result = client.send_message(
                        message=final_result,
                        to_name="orchestrator"
                    )

                    if send_result.get('success'):
                        print(f"[VERIFIER] Sent final result to orchestrator")
                        processed += 1
                    else:
                        print(f"[VERIFIER] Failed to send: {send_result}")

                elif isinstance(message, dict) and message.get('type') == 'shutdown':
                    print("[VERIFIER] Received shutdown signal")
                    break

        time.sleep(0.5)

    print(f"[VERIFIER] Processed {processed} messages, exiting")
    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
