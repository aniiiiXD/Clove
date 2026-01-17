# AgentOS

A microkernel for AI agents. Run multiple AI agents as isolated processes with shared LLM access.

> **"systemd for AI agents"** | **"Docker-lite for autonomous compute"**

## Why AgentOS?

**The Problem:** Python agent frameworks (LangChain, CrewAI, AutoGen) run agents as coroutines or threads. When one agent crashes, leaks memory, or infinite loops - it takes down the entire system.

**The Solution:** AgentOS provides **OS-level isolation**. Each agent is a real process with:
- **Fault isolation** - One agent crashes, others continue
- **Resource limits** - Memory/CPU caps enforced by the kernel (cgroups)
- **Security sandboxing** - Untrusted agents can't access filesystem/network
- **Fair scheduling** - Shared LLM access with rate limiting

**This is literally why operating systems exist** - and AgentOS brings these guarantees to AI agents.

### What AgentOS Can Do That Python Frameworks Can't

| Scenario | Python Frameworks | AgentOS |
|----------|-------------------|---------|
| Agent infinite loops | Entire system hangs | Agent throttled, others continue |
| Agent memory leak | OOM kills everything | Only that agent killed |
| Malicious agent code | Full system access | Sandboxed, access denied |
| 10 agents need LLM | Race conditions | Fair queuing & scheduling |
| Agent crashes | May corrupt shared state | Clean isolation |

## Architecture

AgentOS uses a C++ kernel with a Python subprocess for LLM calls:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AgentOS Kernel (C++23)                        │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Reactor   │  │   LLM Client    │  │   Agent Manager     │  │
│  │   (epoll)   │  │ (subprocess)    │  │   (Sandbox/Fork)    │  │
│  └──────┬──────┘  └────────┬────────┘  └──────────┬──────────┘  │
│         │                  │                       │             │
│         └──────────────────┼───────────────────────┘             │
│                            │                                     │
│              Unix Domain Socket (/tmp/agentos.sock)              │
└────────────────────────────┼─────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │ Agent 1 │          │ Agent 2 │          │ Agent 3 │
   │(Python) │          │(Python) │          │(Python) │
   └─────────┘          └─────────┘          └─────────┘

                             │
                    ┌────────┴────────┐
                    │  LLM Service    │
                    │  (Python)       │
                    │  google-genai   │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   Gemini API    │
                    └─────────────────┘
```

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Unix Socket IPC | Done | Binary protocol with 17-byte header |
| Event Loop | Done | epoll-based reactor pattern |
| LLM Integration | Done | Google Gemini via Python subprocess (google-genai SDK) |
| Multimodal Support | Done | Text + image input to LLM |
| Process Sandboxing | Done | Linux namespaces (PID, NET, MNT, UTS) |
| Resource Limits | Done | cgroups v2 (memory, CPU, PIDs) |
| Python SDK | Done | Full client library with extended think() API |
| Environment Config | Done | Automatic .env file loading |
| **Permission System** | Done | Path validation, command filtering, domain whitelist |
| **HTTP Syscall** | Done | Make HTTP requests with domain restrictions |
| **MCP Server** | Done | Claude Desktop integration via MCP protocol |
| **Framework Adapters** | Done | LangChain, CrewAI, AutoGen integration |

## Requirements

- Linux (Ubuntu 22.04+ / Debian 12+)
- GCC 11+ with C++23 support
- CMake 3.20+
- Python 3.10+
- vcpkg (package manager)

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url> AgentOS
cd AgentOS

# Install vcpkg if you don't have it
git clone https://github.com/Microsoft/vcpkg.git ~/vcpkg
~/vcpkg/bootstrap-vcpkg.sh
export VCPKG_ROOT="$HOME/vcpkg"
```

### 2. Install Dependencies

```bash
# System dependencies
sudo apt install -y build-essential cmake pkg-config libssl-dev python3 python3-pip

# Python dependencies (for LLM service)
pip3 install google-genai
```

### 3. Configure API Key

```bash
# Copy the example .env file
cp .env.example .env

# Edit .env and add your Gemini API key
# Get your key from: https://aistudio.google.com/app/apikey
```

Or set the environment variable directly:
```bash
export GEMINI_API_KEY="your-api-key"
```

### 4. Build

```bash
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

### 5. Run the Kernel

```bash
./agentos_kernel
```

You should see:
```
[info] LLM client initialized (model=gemini-2.0-flash)
[info] Kernel listening on /tmp/agentos.sock
```

### 6. Run an Agent

In another terminal:

```bash
# Simple echo test
python3 agents/examples/hello_agent.py

# LLM interaction
python3 agents/examples/thinking_agent.py

# Spawn/kill agents test
python3 agents/examples/spawn_test.py
```

## OS-Level Demonstrations

These demos prove why AgentOS must exist - they show capabilities that **only** an OS-level kernel can provide.

### Fault Isolation Demo

Spawns 3 agents: a CPU hog, a memory leaker, and a healthy agent. Proves that misbehaving agents don't crash the system.

```bash
# User mode (limited isolation)
python3 agents/examples/fault_isolation_demo.py

# Root mode (full cgroups enforcement)
sudo ./build/agentos_kernel &
sudo python3 agents/examples/fault_isolation_demo.py
```

**What happens:**
```
Agent         Status        Notes
────────────────────────────────────────
cpu-hog       THROTTLED     CPU limited to 10%
mem-hog       KILLED        OOM at 50MB limit
healthy       RUNNING       Unaffected, still working
```

**Why this matters:** This is literally why operating systems exist. Python frameworks can't do this.

## Python SDK Usage

### Basic Usage

```python
import sys
sys.path.insert(0, 'agents/python_sdk')
from agentos import AgentOSClient

with AgentOSClient() as client:
    # Echo test
    response = client.echo("Hello!")
    print(response)  # "Hello!"

    # Simple LLM query
    result = client.think("What is 2+2?")
    print(result['content'])  # "4"
```

### Extended LLM Options

The `think()` method supports multimodal input and advanced configuration:

```python
with AgentOSClient() as client:
    # With system instruction
    result = client.think(
        "Explain quantum computing",
        system_instruction="You are a physics professor. Be concise.",
        temperature=0.5
    )

    # With image input (multimodal)
    with open("photo.jpg", "rb") as f:
        result = client.think(
            "Describe this image",
            image=f.read(),
            image_mime_type="image/jpeg"
        )

    # With thinking level (for reasoning tasks)
    result = client.think(
        "Solve this step by step: What is 15% of 240?",
        thinking_level="high"
    )
```

### Agent Management

```python
with AgentOSClient() as client:
    # Spawn a new agent
    agent = client.spawn(
        name="worker1",
        script="/path/to/worker.py",
        sandboxed=True,
        limits={"memory": 256*1024*1024}
    )
    print(f"Spawned: {agent}")

    # List running agents
    agents = client.list_agents()
    print(agents)

    # Kill an agent
    client.kill(name="worker1")
```

## Permission System

AgentOS implements a comprehensive permission system that controls what agents can access:

### Permission Levels

| Level | Description |
|-------|-------------|
| `unrestricted` | Full access (dangerous!) |
| `standard` | Default safe restrictions |
| `sandboxed` | Strict restrictions, limited paths |
| `readonly` | Can only read, no writes or execution |
| `minimal` | Almost no permissions |

### Setting Permissions

```python
with AgentOSClient() as client:
    # Set permission level
    client.set_permissions(level="standard")

    # Get current permissions
    perms = client.get_permissions()
    print(perms)
```

### Permission Features

- **Path validation** - Glob patterns for allowed/blocked paths
- **Command filtering** - Block dangerous commands (rm -rf, sudo, etc.)
- **Domain whitelist** - HTTP requests limited to approved domains
- **LLM quotas** - Token and call limits per agent

## HTTP Requests

Agents can make HTTP requests through AgentOS with domain restrictions:

```python
with AgentOSClient() as client:
    # Simple GET request
    result = client.http("https://api.github.com/users/octocat")
    print(result['body'])

    # POST with headers and body
    result = client.http(
        url="https://api.example.com/data",
        method="POST",
        headers={"Content-Type": "application/json"},
        body='{"key": "value"}'
    )
```

## Framework Adapters

AgentOS provides adapters for popular AI agent frameworks. All operations go through AgentOS's permission system.

### LangChain

```python
from agents.adapters.langchain_adapter import AgentOSToolkit

# Create toolkit connected to AgentOS
toolkit = AgentOSToolkit(permission_level="standard")
tools = toolkit.get_tools()

# Use with any LangChain agent
from langchain.agents import create_react_agent
agent = create_react_agent(llm, tools, prompt)
```

### CrewAI

```python
from agents.adapters.crewai_adapter import AgentOSCrewAgent

# Create agent factory
factory = AgentOSCrewAgent(permission_level="standard")

# Create pre-configured agents
researcher = factory.create_researcher()
developer = factory.create_developer()
```

### AutoGen

```python
from agents.adapters.autogen_adapter import AgentOSAssistant, AgentOSUserProxy

# Create assistant with AgentOS tools
assistant = AgentOSAssistant(
    name="coder",
    llm_config={"config_list": [{"model": "gpt-4"}]},
    permission_level="standard"
)

# User proxy executes through AgentOS
user_proxy = AgentOSUserProxy(name="user", human_input_mode="NEVER")
user_proxy.initiate_chat(assistant, message="Create a Python script")
```

See `agents/adapters/README.md` for detailed documentation.

## MCP Integration (Claude Desktop)

AgentOS can be used as an MCP server for Claude Desktop, giving Claude controlled access to your PC.

### Setup

1. Start the AgentOS kernel:
```bash
./build/agentos_kernel
```

2. Add to Claude Desktop config (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "agentos": {
      "command": "python3",
      "args": ["/path/to/AGENTOS/agents/mcp/mcp_server.py"]
    }
  }
}
```

3. Restart Claude Desktop

### Available Tools

Once configured, Claude Desktop can use these tools:

| Tool | Description |
|------|-------------|
| `agentos_read` | Read files from filesystem |
| `agentos_write` | Write content to files |
| `agentos_exec` | Execute shell commands |
| `agentos_think` | Query the LLM |
| `agentos_spawn` | Spawn agent processes |
| `agentos_list_agents` | List running agents |
| `agentos_kill` | Kill an agent |
| `agentos_http` | Make HTTP requests |

See `agents/mcp/README.md` for detailed documentation.

## Syscall Reference

| Opcode | Name | Description | Payload | Response |
|--------|------|-------------|---------|----------|
| 0x00 | SYS_NOOP | Echo test | Any bytes | Same bytes |
| 0x01 | SYS_THINK | LLM query | JSON (see below) | JSON: `{success, content, tokens, error}` |
| 0x02 | SYS_READ | Read file | JSON: `{path}` | JSON: `{success, content, size}` |
| 0x03 | SYS_WRITE | Write file | JSON: `{path, content, mode}` | JSON: `{success, bytes_written}` |
| 0x04 | SYS_EXEC | Execute command | JSON: `{command, cwd, timeout}` | JSON: `{success, stdout, stderr, exit_code}` |
| 0x10 | SYS_SPAWN | Spawn agent | JSON config | JSON: `{id, name, pid, status}` |
| 0x11 | SYS_KILL | Kill agent | JSON: `{name}` or `{id}` | JSON: `{killed: bool}` |
| 0x12 | SYS_LIST | List agents | Empty | JSON array of agents |
| 0x40 | SYS_GET_PERMS | Get permissions | Empty | JSON: permission object |
| 0x41 | SYS_SET_PERMS | Set permissions | JSON: permission config | JSON: `{success}` |
| 0x50 | SYS_HTTP | HTTP request | JSON: `{url, method, headers, body}` | JSON: `{success, status_code, body}` |
| 0xFF | SYS_EXIT | Disconnect | Empty | "goodbye" |

### SYS_THINK Request Format

```json
{
  "prompt": "Your question here",
  "image": {
    "data": "<base64-encoded-image>",
    "mime_type": "image/jpeg"
  },
  "system_instruction": "You are a helpful assistant",
  "thinking_level": "low|medium|high",
  "temperature": 0.7,
  "model": "gemini-2.0-flash"
}
```

All fields except `prompt` are optional.

### SYS_THINK Response Format

```json
{
  "success": true,
  "content": "LLM response text",
  "tokens": 123,
  "error": null
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | (none) |
| `GOOGLE_API_KEY` | Fallback API key | (none) |
| `GEMINI_MODEL` | Model to use | gemini-2.0-flash |

### .env File

AgentOS automatically loads configuration from a `.env` file. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Example `.env`:
```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```

The `.env` file is searched in these locations:
1. Current working directory
2. Project root directory
3. Home directory

### Agent Resource Limits

When spawning agents, you can set resource limits:

```python
client.spawn(
    name="worker",
    script="/path/to/script.py",
    sandboxed=True,
    limits={
        "memory": 256 * 1024 * 1024,  # 256MB
        "max_pids": 64,                # Max processes
        "cpu_quota": 100000            # CPU microseconds per period (100% = 100000)
    }
)
```

## Project Structure

```
AgentOS/
├── src/
│   ├── main.cpp                 # Entry point
│   ├── kernel/
│   │   ├── kernel.hpp/cpp       # Main kernel class
│   │   ├── reactor.hpp/cpp      # epoll event loop
│   │   ├── llm_client.hpp/cpp   # LLM subprocess manager
│   │   └── permissions.hpp/cpp  # Permission system
│   ├── ipc/
│   │   ├── protocol.hpp         # Binary protocol definition
│   │   └── socket_server.hpp/cpp # Unix socket server
│   ├── runtime/
│   │   ├── sandbox.hpp/cpp      # Linux namespaces/cgroups
│   │   └── agent_process.hpp/cpp # Agent lifecycle
│   └── util/
│       └── logger.hpp/cpp       # Logging utilities
├── agents/
│   ├── python_sdk/
│   │   └── agentos.py           # Python client library
│   ├── llm_service/
│   │   ├── llm_service.py       # Python LLM subprocess (google-genai)
│   │   └── requirements.txt     # Python dependencies
│   ├── mcp/                     # MCP Server for Claude Desktop
│   │   ├── mcp_server.py        # MCP protocol server
│   │   └── README.md            # Installation instructions
│   ├── adapters/                # Framework adapters
│   │   ├── langchain_adapter.py # LangChain integration
│   │   ├── crewai_adapter.py    # CrewAI integration
│   │   ├── autogen_adapter.py   # AutoGen integration
│   │   └── README.md            # Adapter documentation
│   └── examples/
│       ├── hello_agent.py       # Echo test
│       ├── thinking_agent.py    # LLM interaction
│       ├── worker_agent.py      # Spawnable worker
│       ├── spawn_test.py        # Agent management test
│       ├── fault_isolation_demo.py  # OS-level fault isolation
│       ├── cpu_hog_agent.py     # CPU stress test
│       ├── memory_hog_agent.py  # Memory stress test
│       └── healthy_agent.py     # Well-behaved agent
├── build/                       # Build output
├── CMakeLists.txt              # Build configuration
├── vcpkg.json                  # C++ dependencies
├── .env.example                # Environment template
├── STATUS.md                   # Development status
└── README.md                   # This file
```

## Troubleshooting

### "Permission denied" on socket

```bash
rm -f /tmp/agentos.sock
./agentos_kernel
```

### "LLM not configured" error

Make sure your API key is set:
```bash
# Option 1: Environment variable
export GEMINI_API_KEY="your-api-key"

# Option 2: .env file
echo "GEMINI_API_KEY=your-api-key" > .env
```

### "Could not find llm_service.py"

Make sure you're running from the project directory or build directory:
```bash
cd /path/to/AgentOS/build
./agentos_kernel
```

### Sandbox requires root

Full namespace isolation requires root privileges:

```bash
sudo ./agentos_kernel
```

Without root, agents run with fork() instead of clone() with namespaces.

### Build errors

```bash
# Clean rebuild
rm -rf build
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Python import errors

Install the LLM service dependencies:
```bash
pip3 install google-genai
```

## Development

### Adding a New Syscall

1. Add opcode to `src/ipc/protocol.hpp`
2. Add handler method in `src/kernel/kernel.hpp`
3. Implement handler in `src/kernel/kernel.cpp`
4. Update Python SDK in `agents/python_sdk/agentos.py`

### Running Tests

```bash
# Start kernel
./build/agentos_kernel &

# Run basic tests
python3 agents/examples/hello_agent.py
python3 agents/examples/spawn_test.py
python3 agents/examples/thinking_agent.py

# Run OS-level fault isolation demo
python3 agents/examples/fault_isolation_demo.py

# Stop kernel
pkill agentos_kernel
```

### Running with Full Isolation (requires root)

```bash
# Start kernel with cgroups enabled
sudo ./build/agentos_kernel &

# Run fault isolation demo (will enforce memory/CPU limits)
sudo python3 agents/examples/fault_isolation_demo.py

# Stop kernel
sudo pkill agentos_kernel
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

Built with C++23, powered by Google Gemini.
