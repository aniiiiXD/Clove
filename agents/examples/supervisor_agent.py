#!/usr/bin/env python3
"""
Supervisor Agent - PID 1 Semantics for AI Agents

This agent implements init/systemd-like supervision for other agents:
- Monitors child agents
- Automatically restarts crashed agents
- Tracks restart counts
- Escalates persistent failures

== What This Demonstrates ==

AgentOS enables OS-style supervision patterns:
- Like systemd for services
- Like Kubernetes controllers for pods
- Like Erlang supervisors for actors

== Why This Matters ==

In production agent systems, you need:
- Automatic recovery from crashes
- Restart limits to prevent infinite loops
- Failure escalation for alerting

Python frameworks can't easily do this because agents
run in the same process. AgentOS runs agents as real
processes, enabling true supervision.

"""

import os
import sys
import time
import json

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class SupervisorAgent:
    """Agent supervisor with restart policies"""

    def __init__(self, client):
        self.client = client
        self.supervised = {}  # name -> config
        self.restart_counts = {}  # name -> count
        self.max_restarts = 3
        self.escalated = set()

    def add_child(self, name, script, **kwargs):
        """Add an agent to supervise"""
        self.supervised[name] = {
            'script': script,
            'sandboxed': kwargs.get('sandboxed', True),
            'network': kwargs.get('network', False),
            'limits': kwargs.get('limits', {}),
            'running': False,
            'pid': None,
            'agent_id': None
        }
        self.restart_counts[name] = 0

    def spawn_child(self, name):
        """Spawn a supervised child"""
        if name not in self.supervised:
            print(f"[SUPERVISOR] Unknown child: {name}")
            return False

        config = self.supervised[name]

        # Set environment for child
        os.environ['AGENT_NAME'] = name

        result = self.client.spawn(
            name=name,
            script=config['script'],
            sandboxed=config['sandboxed'],
            network=config['network'],
            limits=config['limits']
        )

        if result and result.get('status') == 'running':
            config['running'] = True
            config['pid'] = result.get('pid')
            config['agent_id'] = result.get('id')
            print(f"[SUPERVISOR] Spawned {name} (PID={config['pid']})")
            return True
        else:
            print(f"[SUPERVISOR] Failed to spawn {name}: {result}")
            return False

    def restart_child(self, name):
        """Restart a failed child with backoff"""
        if name not in self.supervised:
            return False

        if name in self.escalated:
            print(f"[SUPERVISOR] {name} already escalated, not restarting")
            return False

        self.restart_counts[name] += 1
        count = self.restart_counts[name]

        if count > self.max_restarts:
            print(f"[SUPERVISOR] {name} exceeded max restarts ({self.max_restarts})")
            print(f"[SUPERVISOR] ESCALATING: {name} requires manual intervention")
            self.escalated.add(name)
            return False

        print(f"[SUPERVISOR] Restarting {name} (attempt {count}/{self.max_restarts})")

        # Backoff: wait longer between restarts
        backoff = min(count * 2, 10)
        print(f"[SUPERVISOR] Waiting {backoff}s before restart...")
        time.sleep(backoff)

        return self.spawn_child(name)

    def check_children(self):
        """Check all supervised children and restart if needed"""
        agents = self.client.list_agents()
        running_names = set()

        if isinstance(agents, list):
            for agent in agents:
                running_names.add(agent.get('name'))

        restarts_needed = []

        for name, config in self.supervised.items():
            was_running = config['running']
            is_running = name in running_names

            if was_running and not is_running:
                print(f"[SUPERVISOR] Detected {name} has died!")
                config['running'] = False
                config['pid'] = None
                restarts_needed.append(name)
            elif not was_running and is_running:
                config['running'] = True

        # Restart failed children
        for name in restarts_needed:
            self.restart_child(name)

    def process_messages(self):
        """Process messages from children"""
        result = self.client.recv(max_messages=10)
        if not result.get('success'):
            return

        for msg in result.get('messages', []):
            from_name = msg.get('from_name', 'unknown')
            message = msg.get('message', {})

            if isinstance(message, dict):
                msg_type = message.get('type', '')

                if msg_type == 'heartbeat':
                    # Child is alive
                    pass
                elif msg_type == 'crash':
                    print(f"[SUPERVISOR] Received crash notification from {from_name}")

    def get_status(self):
        """Get supervisor status"""
        status = {
            'supervised': len(self.supervised),
            'running': sum(1 for c in self.supervised.values() if c['running']),
            'escalated': len(self.escalated),
            'children': {}
        }

        for name, config in self.supervised.items():
            status['children'][name] = {
                'running': config['running'],
                'pid': config['pid'],
                'restarts': self.restart_counts.get(name, 0),
                'escalated': name in self.escalated
            }

        return status


def main():
    print("=" * 60)
    print("  Supervisor Agent")
    print("  PID 1 semantics for AI agents")
    print("=" * 60)
    print()

    # Connect to kernel
    client = AgentOSClient()
    if not client.connect():
        print("[SUPERVISOR] ERROR: Failed to connect to kernel")
        return 1

    print("[SUPERVISOR] Connected to AgentOS kernel")

    # Register as supervisor
    result = client.register_name("supervisor")
    if result.get("success"):
        print(f"[SUPERVISOR] Registered (id={result.get('agent_id')})")
    print()

    # Create supervisor
    supervisor = SupervisorAgent(client)

    # Add children to supervise
    unstable_script = os.path.join(SCRIPT_DIR, "unstable_agent.py")

    supervisor.add_child("worker-1", unstable_script, sandboxed=False)
    supervisor.add_child("worker-2", unstable_script, sandboxed=False)
    supervisor.add_child("worker-3", unstable_script, sandboxed=False)

    print("[SUPERVISOR] Configured to supervise 3 workers")
    print(f"[SUPERVISOR] Max restarts per worker: {supervisor.max_restarts}")
    print()

    # Spawn all children
    print("[SUPERVISOR] Starting all workers...")
    for name in supervisor.supervised:
        supervisor.spawn_child(name)

    print()
    print("[SUPERVISOR] Entering supervision loop...")
    print("[SUPERVISOR] Workers will crash randomly, supervisor will restart them")
    print()

    # Supervision loop
    try:
        while True:
            # Check for dead children
            supervisor.check_children()

            # Process messages
            supervisor.process_messages()

            # Check if all escalated
            if len(supervisor.escalated) == len(supervisor.supervised):
                print()
                print("[SUPERVISOR] All workers have been escalated!")
                print("[SUPERVISOR] Demo complete - supervisor would alert operator here")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SUPERVISOR] Interrupted by user")

    # Cleanup
    print()
    print("[SUPERVISOR] Final status:")
    status = supervisor.get_status()
    for name, info in status['children'].items():
        escalated = " (ESCALATED)" if info['escalated'] else ""
        print(f"  {name}: restarts={info['restarts']}, running={info['running']}{escalated}")

    # Kill remaining children
    print()
    print("[SUPERVISOR] Cleaning up children...")
    for name in supervisor.supervised:
        try:
            client.kill(name=name)
        except:
            pass

    client.disconnect()
    print("[SUPERVISOR] Shutdown complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
