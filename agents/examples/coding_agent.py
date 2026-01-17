#!/usr/bin/env python3
"""
Coding Agent Example - AgentOS Agentic Loop Demo

Demonstrates the agentic loop capability where an LLM-powered agent can:
- Execute shell commands (python3, gcc, ls, etc.)
- Read and write files
- Reason iteratively to complete complex tasks

Similar to Claude Code's autonomous coding capabilities.

Usage:
    python3 agents/examples/coding_agent.py

Requires:
    - AgentOS kernel running (./build/agentos_kernel)
    - GEMINI_API_KEY environment variable set
"""

import sys
import os

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient
from agentic import AgenticLoop, AgentResult


def print_banner():
    print("=" * 70)
    print("  AgentOS Coding Agent - LLM-Powered Agentic Loop")
    print("  Execute commands, read/write files, and reason iteratively")
    print("=" * 70)
    print()


def print_result(result: AgentResult):
    """Pretty print the agent result"""
    print()
    print("-" * 50)
    if result.success:
        print(f"SUCCESS after {result.iterations} iteration(s)")
        print(f"Result: {result.result}")
    else:
        print(f"FAILED after {result.iterations} iteration(s)")
        if result.error:
            print(f"Error: {result.error}")
    print("-" * 50)


def run_demo_tasks(client: AgentOSClient):
    """Run a few demo tasks to showcase capabilities"""
    print("[Demo Mode] Running example tasks...\n")

    demo_tasks = [
        "List the files in the current directory using ls -la",
        "Create a Python file called /tmp/hello_agentos.py that prints 'Hello from AgentOS!' and run it",
    ]

    for i, task in enumerate(demo_tasks, 1):
        print(f"\n{'='*60}")
        print(f"Demo Task {i}: {task}")
        print('='*60 + '\n')

        loop = AgenticLoop(client, max_iterations=10, verbose=True)
        result = loop.run(task)
        print_result(result)

        if i < len(demo_tasks):
            print("\n[Press Enter for next demo task or Ctrl+C to exit]")
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                print("\nSkipping remaining demos...")
                break


def run_interactive(client: AgentOSClient):
    """Run in interactive mode"""
    print("[Interactive Mode]")
    print("Enter a task for the agent to complete.")
    print("Examples:")
    print("  - List files in current directory")
    print("  - Create a hello.py file and run it")
    print("  - Read /etc/hostname and tell me what it says")
    print("  - Compile and run a C program that prints 'Hello World'")
    print()
    print("Type 'demo' to run demo tasks, 'exit' to quit.")
    print()

    loop = AgenticLoop(client, max_iterations=20, verbose=True)

    while True:
        try:
            task = input("\nTask: ").strip()

            if not task:
                continue

            if task.lower() == 'exit':
                print("Goodbye!")
                break

            if task.lower() == 'demo':
                run_demo_tasks(client)
                continue

            # Run the task
            print()
            result = loop.run(task)
            print_result(result)

            # Reset conversation for next task
            loop.conversation_history = []

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit or enter a new task.")
        except EOFError:
            print("\nGoodbye!")
            break


def main():
    print_banner()

    # Check for API key
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        print("WARNING: No GEMINI_API_KEY or GOOGLE_API_KEY found in environment.")
        print("The agent will not be able to use the LLM for reasoning.")
        print()

    # Connect to kernel
    print("[Connecting to AgentOS kernel...]")
    try:
        with AgentOSClient() as client:
            # Test connection
            echo_result = client.echo("test")
            if echo_result is None:
                print("ERROR: Could not connect to AgentOS kernel.")
                print("Make sure the kernel is running: ./build/agentos_kernel")
                sys.exit(1)

            print("[Connected successfully!]")
            print()

            # Check for command line args
            if len(sys.argv) > 1:
                if sys.argv[1] == '--demo':
                    run_demo_tasks(client)
                else:
                    # Treat args as a task
                    task = ' '.join(sys.argv[1:])
                    print(f"[Running task: {task}]\n")
                    loop = AgenticLoop(client, max_iterations=20, verbose=True)
                    result = loop.run(task)
                    print_result(result)
            else:
                run_interactive(client)

    except ConnectionError as e:
        print(f"ERROR: {e}")
        print("Make sure the AgentOS kernel is running: ./build/agentos_kernel")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
