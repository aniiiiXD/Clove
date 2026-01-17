#!/usr/bin/env python3
"""
IPC Demo - Inter-Agent Communication Example

Demonstrates agent-to-agent communication through the kernel:
- Agent registration with names
- Sending messages to specific agents
- Receiving messages
- Broadcasting to all agents

Usage:
    # Terminal 1: Start the kernel
    ./build/agentos_kernel

    # Terminal 2: Run agent 1 (receiver)
    python3 agents/examples/ipc_demo.py receiver

    # Terminal 3: Run agent 2 (sender)
    python3 agents/examples/ipc_demo.py sender

    # Or run the interactive demo:
    python3 agents/examples/ipc_demo.py
"""

import sys
import os
import time
import threading

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient


def run_receiver():
    """Run as a receiver agent that listens for messages"""
    print("=" * 50)
    print("  IPC Demo - RECEIVER Agent")
    print("=" * 50)
    print()

    with AgentOSClient() as client:
        # Register with name
        result = client.register_name("receiver")
        if not result.get("success"):
            print(f"Failed to register: {result.get('error')}")
            return

        print(f"Registered as 'receiver' (agent_id: {result.get('agent_id')})")
        print("Waiting for messages... (Ctrl+C to stop)")
        print()

        try:
            while True:
                # Poll for messages
                result = client.recv(max_messages=10)

                if result.get("success") and result.get("count", 0) > 0:
                    for msg in result["messages"]:
                        sender = msg.get("from_name") or f"agent_{msg.get('from')}"
                        content = msg.get("message", {})
                        age_ms = msg.get("age_ms", 0)

                        print(f"[Message from {sender}] (age: {age_ms}ms)")
                        print(f"  {content}")
                        print()

                time.sleep(0.5)  # Poll every 500ms

        except KeyboardInterrupt:
            print("\nReceiver stopped.")


def run_sender():
    """Run as a sender agent that sends messages"""
    print("=" * 50)
    print("  IPC Demo - SENDER Agent")
    print("=" * 50)
    print()

    with AgentOSClient() as client:
        # Register with name
        result = client.register_name("sender")
        if not result.get("success"):
            print(f"Failed to register: {result.get('error')}")
            return

        print(f"Registered as 'sender' (agent_id: {result.get('agent_id')})")
        print()
        print("Commands:")
        print("  send <message>    - Send to 'receiver' agent")
        print("  broadcast <msg>   - Broadcast to all agents")
        print("  exit              - Quit")
        print()

        try:
            while True:
                cmd = input("sender> ").strip()

                if not cmd:
                    continue

                if cmd.lower() == "exit":
                    print("Goodbye!")
                    break

                if cmd.startswith("send "):
                    message_text = cmd[5:].strip()
                    result = client.send(
                        message={"type": "text", "content": message_text},
                        to_name="receiver"
                    )
                    if result.get("success"):
                        print(f"  -> Delivered to agent {result.get('delivered_to')}")
                    else:
                        print(f"  -> Failed: {result.get('error')}")

                elif cmd.startswith("broadcast "):
                    message_text = cmd[10:].strip()
                    result = client.broadcast(
                        message={"type": "broadcast", "content": message_text}
                    )
                    if result.get("success"):
                        print(f"  -> Broadcasted to {result.get('delivered_count')} agents")
                    else:
                        print(f"  -> Failed: {result.get('error')}")

                else:
                    print("  Unknown command. Use 'send <msg>' or 'broadcast <msg>'")

        except KeyboardInterrupt:
            print("\nSender stopped.")
        except EOFError:
            print("\nGoodbye!")


def run_interactive_demo():
    """Run an interactive demo showing IPC between two simulated agents"""
    print("=" * 60)
    print("  IPC Demo - Interactive Mode")
    print("  Demonstrates agent-to-agent communication")
    print("=" * 60)
    print()

    # Use two separate connections to simulate two agents
    agent1 = AgentOSClient()
    agent2 = AgentOSClient()

    if not agent1.connect() or not agent2.connect():
        print("Failed to connect to kernel. Make sure it's running.")
        return

    try:
        # Register both agents
        print("[Step 1] Registering agents...")
        r1 = agent1.register_name("alice")
        r2 = agent2.register_name("bob")

        print(f"  Alice registered: agent_id={r1.get('agent_id')}")
        print(f"  Bob registered: agent_id={r2.get('agent_id')}")
        print()

        # Alice sends message to Bob
        print("[Step 2] Alice sends a message to Bob...")
        result = agent1.send(
            message={"greeting": "Hello Bob! How are you?"},
            to_name="bob"
        )
        print(f"  Send result: {result}")
        print()

        # Bob receives the message
        print("[Step 3] Bob checks his mailbox...")
        result = agent2.recv()
        print(f"  Recv result: {result}")

        if result.get("messages"):
            msg = result["messages"][0]
            print(f"  Bob received from {msg.get('from_name')}: {msg.get('message')}")
        print()

        # Bob replies
        print("[Step 4] Bob sends a reply to Alice...")
        result = agent2.send(
            message={"reply": "Hi Alice! I'm doing great, thanks!"},
            to_name="alice"
        )
        print(f"  Send result: {result}")
        print()

        # Alice receives the reply
        print("[Step 5] Alice checks her mailbox...")
        result = agent1.recv()
        print(f"  Recv result: {result}")

        if result.get("messages"):
            msg = result["messages"][0]
            print(f"  Alice received from {msg.get('from_name')}: {msg.get('message')}")
        print()

        # Broadcast example
        print("[Step 6] Alice broadcasts to everyone...")
        result = agent1.broadcast(
            message={"announcement": "Meeting at 3pm!"},
            include_self=False
        )
        print(f"  Broadcast result: {result}")
        print()

        # Bob receives the broadcast
        print("[Step 7] Bob receives the broadcast...")
        result = agent2.recv()
        print(f"  Bob received: {result}")
        print()

        print("=" * 60)
        print("  Demo complete!")
        print("=" * 60)

    finally:
        agent1.disconnect()
        agent2.disconnect()


def main():
    if len(sys.argv) < 2:
        run_interactive_demo()
    elif sys.argv[1] == "receiver":
        run_receiver()
    elif sys.argv[1] == "sender":
        run_sender()
    else:
        print(f"Unknown mode: {sys.argv[1]}")
        print("Usage: python3 ipc_demo.py [receiver|sender]")
        print("       python3 ipc_demo.py  (interactive demo)")
        sys.exit(1)


if __name__ == "__main__":
    main()
