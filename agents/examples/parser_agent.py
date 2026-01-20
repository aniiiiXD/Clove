#!/usr/bin/env python3
"""
Parser Agent - Stage 1 of Agent Pipeline

This agent receives raw input, parses/preprocesses it,
and passes the structured result to the next stage.
"""

import os
import sys
import time
import json
import re

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient


def parse_math_expression(text):
    """Parse a natural language math question into structured form"""
    # Extract numbers
    numbers = re.findall(r'\d+', text)

    # Detect operation
    operation = None
    if any(word in text.lower() for word in ['add', 'plus', 'sum', '+']):
        operation = 'add'
    elif any(word in text.lower() for word in ['subtract', 'minus', 'difference', '-']):
        operation = 'subtract'
    elif any(word in text.lower() for word in ['multiply', 'times', 'product', '*', 'x']):
        operation = 'multiply'
    elif any(word in text.lower() for word in ['divide', 'quotient', '/', 'divided']):
        operation = 'divide'

    return {
        'original': text,
        'numbers': [int(n) for n in numbers],
        'operation': operation,
        'parsed_at': time.time()
    }


def log(msg):
    """Debug log to file"""
    with open('/tmp/parser_agent.log', 'a') as f:
        f.write(f"{msg}\n")
        f.flush()

def main():
    log("[PARSER] Starting parser agent")
    print("[PARSER] Starting parser agent", flush=True)

    # Connect to kernel
    client = AgentOSClient()
    log(f"[PARSER] Connecting...")
    if not client.connect():
        log("[PARSER] ERROR: Failed to connect to kernel")
        print("[PARSER] ERROR: Failed to connect to kernel", flush=True)
        return 1

    log("[PARSER] Connected, registering...")
    # Register
    result = client.register_name("parser")
    log(f"[PARSER] Register result: {result}")
    if result.get("success"):
        print(f"[PARSER] Registered (id={result.get('agent_id')})", flush=True)

    print("[PARSER] Waiting for input from orchestrator...")

    # Wait for messages
    processed = 0
    while processed < 5:  # Process up to 5 messages then exit
        # Check for messages
        recv_result = client.recv_messages(max_messages=1)

        if recv_result.get('success') and recv_result.get('count', 0) > 0:
            for msg in recv_result.get('messages', []):
                message = msg.get('message', {})

                if isinstance(message, dict) and message.get('type') == 'parse_request':
                    input_text = message.get('input', '')
                    request_id = message.get('request_id', 0)

                    print(f"[PARSER] Received: '{input_text}'")

                    # Parse the input
                    parsed = parse_math_expression(input_text)
                    parsed['request_id'] = request_id
                    parsed['type'] = 'parsed_data'

                    print(f"[PARSER] Parsed: numbers={parsed['numbers']}, op={parsed['operation']}")

                    # Send to reasoner
                    send_result = client.send_message(
                        message=parsed,
                        to_name="reasoner"
                    )

                    if send_result.get('success'):
                        print(f"[PARSER] Sent to reasoner")
                        processed += 1
                    else:
                        print(f"[PARSER] Failed to send: {send_result}")

                elif isinstance(message, dict) and message.get('type') == 'shutdown':
                    print("[PARSER] Received shutdown signal")
                    break

        time.sleep(0.5)

    print(f"[PARSER] Processed {processed} messages, exiting")
    client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
