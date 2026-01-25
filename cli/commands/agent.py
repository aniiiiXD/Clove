#!/usr/bin/env python3
"""
AgentOS CLI - Agent Commands

Deploy and manage agents on remote kernels.
"""

import click
import subprocess
import sys
import os
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from cli.relay_api import SyncRelayAPIClient, RelayAPIError


console = Console() if RICH_AVAILABLE else None


def echo(message, style=None):
    """Print message with optional rich styling."""
    if RICH_AVAILABLE and style:
        console.print(message, style=style)
    else:
        click.echo(message)


@click.group()
def agent():
    """Manage agents on remote kernels."""
    pass


@agent.command('run')
@click.argument('script', type=click.Path(exists=True))
@click.option('--machine', '-m', help='Target machine ID')
@click.option('--all', 'run_all', is_flag=True, help='Run on all machines')
@click.option('--env', '-e', multiple=True, help='Environment variables (KEY=VALUE)')
@click.option('--args', '-a', multiple=True, help='Script arguments')
@click.option('--relay', '-r', help='Relay server URL (for remote agents)')
@click.option('--local', '-l', is_flag=True, help='Run locally via SDK')
@click.pass_context
def run_agent(ctx, script, machine, run_all, env, args, relay, local):
    """Run an agent script on a machine."""
    cfg = ctx.obj['config']

    script_path = Path(script).resolve()
    if not script_path.exists():
        echo(f"Script not found: {script}", style="bold red")
        sys.exit(1)

    # Determine target machines
    if run_all:
        machines = list(cfg.list_machines().keys())
        if not machines:
            echo("No machines registered", style="bold red")
            sys.exit(1)
        echo(f"Running on {len(machines)} machines...", style="blue")

    elif machine:
        machines = [machine]

    else:
        # Try to get machine from environment
        machine = os.environ.get('AGENTOS_MACHINE')
        if machine:
            machines = [machine]
        else:
            echo("Error: No machine specified", style="bold red")
            echo("Use --machine <id> or set AGENTOS_MACHINE environment variable")
            sys.exit(1)

    # Build environment variables
    env_vars = dict(os.environ)
    for e in env:
        key, _, value = e.partition('=')
        env_vars[key] = value

    if local:
        # Run locally using the Python SDK
        for mid in machines:
            _run_local(cfg, mid, script_path, list(args), env_vars)
    else:
        # Deploy via relay API
        relay_url = relay or cfg.relay_api_url
        _run_via_relay(cfg, relay_url, machines, script_path, list(args))


def _run_local(cfg, machine_id, script_path, args, env_vars):
    """Run agent locally using Python SDK."""
    machine = cfg.get_machine(machine_id)

    if machine:
        env_vars['AGENTOS_MACHINE'] = machine_id
        env_vars['AGENTOS_TOKEN'] = machine.get('token', '')
        env_vars['RELAY_URL'] = machine.get('relay_url', cfg.relay_url)

    echo(f"\nRunning agent on {machine_id}...", style="blue")

    cmd = ['python', str(script_path)] + args
    result = subprocess.run(cmd, env=env_vars)

    if result.returncode != 0:
        echo(f"Agent exited with code {result.returncode}", style="yellow")


def _run_via_relay(cfg, relay_url, machines, script_path, args):
    """Deploy agent via relay API."""
    try:
        client = SyncRelayAPIClient(relay_url, cfg.api_token)

        for mid in machines:
            echo(f"\nDeploying agent to {mid}...", style="blue")

            try:
                result = client.deploy_agent(str(script_path), mid, args)
                agent_id = result.get('agent_id', 'unknown')
                echo(f"  Agent deployed: {agent_id}", style="green")

                # Show any output
                if 'output' in result:
                    echo("\nAgent output:")
                    for line in result['output'].split('\n'):
                        echo(f"  > {line}")

            except RelayAPIError as e:
                echo(f"  Failed: {e}", style="bold red")

    except RelayAPIError as e:
        echo(f"Error connecting to relay: {e}", style="bold red")
        sys.exit(1)


@agent.command('list')
@click.option('--machine', '-m', help='Filter by machine ID')
@click.option('--relay', '-r', help='Relay server API URL')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list_agents(ctx, machine, relay, as_json):
    """List running agents."""
    cfg = ctx.obj['config']
    relay_url = relay or cfg.relay_api_url

    try:
        client = SyncRelayAPIClient(relay_url, cfg.api_token)
        agents = client.list_agents(machine)

        if as_json:
            import json
            click.echo(json.dumps([a.__dict__ for a in agents], indent=2))
            return

        if not agents:
            echo("No agents running", style="dim")
            return

        if RICH_AVAILABLE:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Agent ID")
            table.add_column("Name")
            table.add_column("Machine")
            table.add_column("Syscalls")
            table.add_column("Connected")

            for a in agents:
                table.add_row(
                    str(a.agent_id),
                    a.agent_name,
                    a.target_machine,
                    str(a.syscalls_sent),
                    a.connected_at[:19] if a.connected_at else "-"
                )

            console.print(table)
        else:
            for a in agents:
                click.echo(f"[{a.agent_id}] {a.agent_name} -> {a.target_machine} ({a.syscalls_sent} syscalls)")

    except RelayAPIError as e:
        if 'Connection' in str(e):
            echo(f"Relay server not reachable at {relay_url}", style="yellow")
        else:
            echo(f"Error: {e}", style="bold red")
        sys.exit(1)


@agent.command('stop')
@click.argument('agent_id', type=int)
@click.option('--machine', '-m', required=True, help='Machine ID')
@click.option('--relay', '-r', help='Relay server API URL')
@click.pass_context
def stop_agent(ctx, agent_id, machine, relay):
    """Stop a running agent."""
    cfg = ctx.obj['config']
    relay_url = relay or cfg.relay_api_url

    try:
        client = SyncRelayAPIClient(relay_url, cfg.api_token)
        client.stop_agent(machine, agent_id)
        echo(f"Agent {agent_id} stopped", style="green")

    except RelayAPIError as e:
        echo(f"Error: {e}", style="bold red")
        sys.exit(1)


@agent.command('create')
@click.argument('name')
@click.option('--template', '-t', type=click.Choice(['basic', 'worker', 'supervisor']),
              default='basic', help='Agent template')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
def create_agent(name, template, output):
    """Create a new agent from template."""

    templates = {
        'basic': '''#!/usr/bin/env python3
"""
{name} Agent
"""

import sys
sys.path.insert(0, 'agents/python_sdk')

from clove_sdk import AgentOS

def main():
    agent = AgentOS("{name}")

    # Write a message
    agent.write("Hello from {name}!")

    # Your agent logic here
    # ...

    agent.exit(0)

if __name__ == "__main__":
    main()
''',
        'worker': '''#!/usr/bin/env python3
"""
{name} Worker Agent
"""

import sys
import time
sys.path.insert(0, 'agents/python_sdk')

from clove_sdk import AgentOS

def main():
    agent = AgentOS("{name}")

    agent.write("Starting worker agent...")

    # Main work loop
    for i in range(10):
        agent.write(f"Working... iteration {{i+1}}")
        time.sleep(1)

    agent.write("Work complete!")
    agent.exit(0)

if __name__ == "__main__":
    main()
''',
        'supervisor': '''#!/usr/bin/env python3
"""
{name} Supervisor Agent
"""

import sys
sys.path.insert(0, 'agents/python_sdk')

from clove_sdk import AgentOS

def main():
    agent = AgentOS("{name}")

    agent.write("Supervisor starting...")

    # Spawn child agents
    child_pids = []
    for i in range(3):
        pid = agent.spawn(f"worker_{{i}}.py")
        if pid > 0:
            agent.write(f"Spawned worker {{i}}: PID {{pid}}")
            child_pids.append(pid)

    # Wait for children
    for pid in child_pids:
        agent.waitpid(pid)
        agent.write(f"Worker {{pid}} completed")

    agent.write("All workers complete!")
    agent.exit(0)

if __name__ == "__main__":
    main()
'''
    }

    content = templates[template].format(name=name)

    if output:
        output_path = Path(output)
    else:
        output_path = Path(f"{name.lower().replace(' ', '_')}_agent.py")

    output_path.write_text(content)
    output_path.chmod(0o755)

    echo(f"Created agent: {output_path}", style="green")
    echo(f"\nRun with:")
    echo(f"  agentos agent run {output_path} --machine <machine_id>")
