# AgentOS Python SDK

Python client library for communicating with the AgentOS kernel.

## Installation

```bash
# SDK is included in the repo, just add to path
export PYTHONPATH="/path/to/AgentOS/agents/python_sdk:$PYTHONPATH"

# Or copy to your project
cp agents/python_sdk/agentos.py your_project/
```

## Quick Start

```python
from agentos import AgentOSClient

with AgentOSClient() as client:
    # Echo test
    result = client.noop("Hello AgentOS!")
    print(result)

    # LLM query
    response = client.think("Explain quantum computing in one sentence")
    print(response['content'])
```

## Files

| File | Description |
|------|-------------|
| `agentos.py` | Core SDK - `AgentOSClient` class with all syscalls |
| `agentic.py` | Agentic loop framework - autonomous task execution |

## AgentOSClient API

### Connection

```python
client = AgentOSClient(socket_path='/tmp/agentos.sock')
client.connect()
# ... use client ...
client.disconnect()

# Or use context manager (recommended)
with AgentOSClient() as client:
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

## Agentic Loop

For autonomous task execution with LLM reasoning:

```python
from agentic import run_task, AgenticLoop

# Quick usage
result = run_task("Create a Python script that prints Fibonacci numbers")

# With more control
with AgentOSClient() as client:
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
with AgentOSClient() as client:
    result = client.think("Hello")

    if not result.get('success'):
        print(f"Error: {result.get('error')}")
    else:
        print(result['content'])
```
