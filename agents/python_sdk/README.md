# Clove Python SDK

Python client library for communicating with the Clove kernel.

## Installation

```bash
# SDK is included in the repo, just add to path
export PYTHONPATH="/path/to/Clove/agents/python_sdk:$PYTHONPATH"

# Or copy to your project
cp agents/python_sdk/agentos.py your_project/
```

## Quick Start

```python
from clove_sdk import CloveClient

with CloveClient() as client:
    # Echo test
    result = client.noop("Hello Clove!")
    print(result)

    # LLM query
    response = client.think("Explain quantum computing in one sentence")
    print(response['content'])
```

## Files

| File | Description |
|------|-------------|
| `agentos.py` | Core SDK - `CloveClient` class with all syscalls |
| `agentic.py` | Agentic loop framework - autonomous task execution |
| `fleet_client.py` | Fleet management - deploy agents to remote machines |
| `remote_client.py` | Remote agent SDK - run agents via relay server |

## CloveClient API

### Connection

```python
client = CloveClient(socket_path='/tmp/clove.sock')
client.connect()
# ... use client ...
client.disconnect()

# Or use context manager (recommended)
with CloveClient() as client:
    pass
```

### LLM

```python
# Basic
response = client.think("What is 2+2?")

# With options
response = client.think(
    prompt="Describe this image",
    image={"data": base64_data, "mime_type": "image/jpeg"},
    system_instruction="You are a helpful assistant",
    thinking_level="medium",  # low, medium, high
    temperature=0.7
)
```

### Agent Management

```python
# Spawn
agent = client.spawn(
    name="worker",
    script="/path/to/agent.py",
    sandboxed=True,
    limits={"memory": 256*1024*1024, "max_pids": 64}
)

# List
agents = client.list_agents()

# Kill
client.kill(name="worker")
# or
client.kill(agent_id=123)
```

### File Operations

```python
# Read
result = client.read_file("/tmp/data.txt")
content = result['content']

# Write
client.write_file("/tmp/output.txt", "Hello World")
client.write_file("/tmp/log.txt", "New line\n", mode="append")
```

### Command Execution

```python
result = client.exec("ls -la /tmp")
print(result['stdout'])
print(result['exit_code'])
```

### HTTP Requests

```python
result = client.http("https://api.github.com/users/octocat")
data = json.loads(result['body'])
```

### Inter-Agent Communication

```python
# Register name
client.register_name("orchestrator")

# Send to specific agent
client.send_message({"task": "process"}, to_name="worker")

# Receive messages
messages = client.recv_messages()

# Broadcast to all
client.broadcast({"event": "shutdown"})
```

### Permissions

```python
# Get current permissions
perms = client.get_permissions()

# Set permissions (requires elevated privileges)
client.set_permissions(level="sandboxed")
```

### Metrics

```python
# System metrics (CPU, memory, disk, network)
metrics = client.get_system_metrics()
print(f"CPU: {metrics['metrics']['cpu']['percent']}%")
print(f"Memory: {metrics['metrics']['memory']['percent']}%")

# Agent metrics
agent_metrics = client.get_agent_metrics(agent_id=123)
print(f"Process CPU: {agent_metrics['metrics']['process']['cpu']['percent']}%")

# All agent metrics
all_agents = client.get_all_agent_metrics()
for agent in all_agents['agents']:
    print(f"{agent['name']}: {agent['process']['cpu']['percent']}%")

# Cgroup metrics (if sandboxed)
cgroup = client.get_cgroup_metrics()
if cgroup.get('success'):
    print(f"Memory usage: {cgroup['metrics']['memory']['current']}")
```

## Agentic Loop

For autonomous task execution with LLM reasoning:

```python
from agentic import run_task, AgenticLoop

# Quick usage
result = run_task("Create a Python script that prints Fibonacci numbers")

# With more control
with CloveClient() as client:
    loop = AgenticLoop(client, max_iterations=20, verbose=True)
    result = loop.run("Find all TODO comments in the codebase")
    print(f"Completed in {result.iterations} iterations")
    print(result.result)
```

### Built-in Tools

| Tool | Description |
|------|-------------|
| `exec` | Execute shell commands |
| `read_file` | Read file contents |
| `write_file` | Write/create files |
| `done` | Signal task completion |

### Custom Tools

```python
from agentic import AgenticLoop, Tool

loop = AgenticLoop(client)

# Add custom tool
loop.add_tool(Tool(
    name="search",
    description="Search the web",
    parameters={"type": "object", "properties": {"query": {"type": "string"}}},
    handler=lambda args: {"results": do_search(args['query'])}
))
```

## Error Handling

```python
with CloveClient() as client:
    result = client.think("Hello")

    if not result.get('success'):
        print(f"Error: {result.get('error')}")
    else:
        print(result['content'])
```

## Fleet Client

For managing remote agent deployment across multiple machines.

### Quick Start

```python
from fleet_client import FleetClient, SyncFleetClient

# Async usage
async def main():
    fleet = FleetClient(relay_url="http://localhost:8766")

    # List machines
    machines = await fleet.list_machines()
    for m in machines:
        print(f"{m.machine_id}: {m.status}")

    # Deploy agent
    result = await fleet.deploy_agent(
        "my_agent.py",
        machine_id="docker-dev-abc123"
    )

    await fleet.close()

# Sync usage
fleet = SyncFleetClient(relay_url="http://localhost:8766")
machines = fleet.list_machines()
fleet.deploy_agent("my_agent.py", machine_id="docker-dev-abc123")
```

### FleetClient API

```python
# Machine operations
machines = await fleet.list_machines()
machine = await fleet.get_machine("machine-id")
connected = await fleet.get_connected_machines()

# Agent operations
agents = await fleet.list_agents()
agents = await fleet.list_agents(machine_id="m1")
result = await fleet.deploy_agent("script.py", machine_id="m1")
results = await fleet.run_on_all("health.py")
await fleet.stop_agent(machine_id="m1", agent_id=42)

# Fleet status
status = await fleet.get_status()
healthy = await fleet.health_check()
```

### Data Classes

```python
from fleet_client import Machine, Agent

# Machine
machine.machine_id      # "docker-dev-abc123"
machine.provider        # "docker" | "aws" | "gcp"
machine.status          # "connected" | "disconnected"
machine.ip_address      # "172.17.0.2"
machine.is_connected()  # True/False

# Agent
agent.agent_id          # 42
agent.agent_name        # "my_agent"
agent.target_machine    # "docker-dev-abc123"
agent.status            # "running" | "stopped"
agent.syscalls_sent     # 15
```

### Run on All Machines

```python
# Deploy to all connected machines
results = await fleet.run_on_all("health_check.py")

# With filtering
results = await fleet.run_on_all(
    "cleanup.py",
    filter_fn=lambda m: m.provider == "docker"
)

for result in results:
    print(f"{result['machine_id']}: {result['status']}")
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RELAY_API_URL` | Relay server URL | `http://localhost:8766` |
| `AGENTOS_API_TOKEN` | Auth token | (none) |

## Remote Client

For running agents that connect through the relay server.

```python
from remote_client import RemoteClove

agent = RemoteClove(
    name="my_agent",
    relay_url="ws://relay.example.com:8765",
    token="your_agent_token"
)

# Use like normal Clove
agent.write("Hello from remote!")
result = agent.think("What is 2+2?")
agent.exit(0)
```
