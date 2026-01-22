# Clove

A microkernel operating system for AI agents. Run multiple autonomous agents as isolated processes with OS-level guarantees.

> **"systemd for AI agents"** | **"Docker-lite for autonomous compute"**

## Why Clove?

**The Problem:** Python agent frameworks (LangChain, CrewAI, AutoGen) run agents as coroutines or threads. When one agent crashes, leaks memory, or infinite loops - it takes down the entire system.

**The Solution:** Clove provides **OS-level isolation**. Each agent is a real process with:
- **Fault isolation** - One agent crashes, others continue
- **Resource limits** - Memory/CPU caps enforced by the kernel (cgroups)
- **Security sandboxing** - Untrusted agents can't access filesystem/network
- **Fair scheduling** - Shared LLM access with rate limiting

**This is literally why operating systems exist** - and Clove brings these guarantees to AI agents.

### What Clove Can Do That Python Frameworks Can't

| Scenario | Python Frameworks | Clove |
|----------|-------------------|---------|
| Agent infinite loops | Entire system hangs | Agent throttled, others continue |
| Agent memory leak | OOM kills everything | Only that agent killed |
| Malicious agent code | Full system access | Sandboxed, access denied |
| 10 agents need LLM | Race conditions | Fair queuing & scheduling |
| Agent crashes | May corrupt shared state | Clean isolation |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Clove Kernel (C++23)                          │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Reactor   │  │   LLM Client    │  │   Agent Manager     │  │
│  │   (epoll)   │  │ (subprocess)    │  │   (Sandbox/Fork)    │  │
│  └──────┬──────┘  └────────┬────────┘  └──────────┬──────────┘  │
│         │                  │                       │             │
│         └──────────────────┼───────────────────────┘             │
│                            │                                     │
│              Unix Domain Socket (/tmp/clove.sock)                │
└────────────────────────────┼─────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │ Agent 1 │          │ Agent 2 │          │ Agent 3 │
   │(Python) │          │(Python) │          │(Python) │
   └─────────┘          └─────────┘          └─────────┘
```

## Current Features

| Feature | Status | Description |
|---------|--------|-------------|
| Unix Socket IPC | Done | Binary protocol with 17-byte header |
| Event Loop | Done | epoll-based reactor pattern |
| LLM Integration | Done | Google Gemini via Python subprocess |
| Multimodal Support | Done | Text + image input to LLM |
| Process Sandboxing | Done | Linux namespaces (PID, NET, MNT, UTS) |
| Resource Limits | Done | cgroups v2 (memory, CPU, PIDs) |
| Python SDK | Done | Full client library |
| Permission System | Done | Path validation, command filtering, domain whitelist |
| HTTP Syscall | Done | Make HTTP requests with domain restrictions |
| MCP Server | Done | Claude Desktop integration via MCP protocol |
| Framework Adapters | Done | LangChain, CrewAI, AutoGen integration |
| Web Dashboard | Done | Real-time browser-based monitoring UI |
| Agentic Loop | Done | Claude Code-style autonomous agent framework |
| Remote Connectivity | Done | Relay server for cloud agent connections |
| Cloud Deployment | Done | CLI for deploying to Docker, AWS, GCP |
| **Metrics System** | **Done** | **Kernel-level CPU, memory, disk, network metrics** |

## Quick Demo: Crash Isolation

See Clove's core value proposition in action:

```bash
# Terminal 1: Start kernel
./build/clove_kernel

# Terminal 2: Run the crash isolation demo
python demos/crash_isolation_demo.py
```

This demo spawns 3 agents, crashes one, and shows the others continue unaffected.

## Metrics TUI

Real-time terminal dashboard for monitoring Clove kernel.

```bash
# Make sure kernel is running
./build/clove_kernel &

# Launch TUI
python3 agents/dashboard/metrics_tui.py
```

```
┌──────────────────────────────────────────────────────────────────┐
│ ● CONNECTED        ◆ CLOVE Metrics Dashboard          ⏱ 14:32:05 │
├────────────────────────────────┬─────────────────────────────────┤
│ System Metrics                 │ Agents (3)                      │
│                                │                                 │
│ CPU     ████████░░░░  42.3%    │ ID  Name         Status    CPU  │
│ Load    1.24 / 0.98 / 0.76     │ 1   coordinator  ● running 2.1% │
│ Memory  ██████░░░░ 3.2GB/8GB   │ 2   researcher   ● running 5.3% │
│ Disk    R: 124MB | W: 56MB     │ 3   writer       ● running 1.2% │
│ Network ↓ 1.2GB | ↑ 340MB      │                                 │
├────────────────────────────────┴─────────────────────────────────┤
│ Updated: 14:32:05     [q] Quit  [r] Refresh                      │
└──────────────────────────────────────────────────────────────────┘
```

**Features:**
- Live CPU, memory, disk, and network metrics
- Agent list with status and resource usage
- Auto-refresh every 2 seconds
- Keyboard controls (q=quit, r=refresh)

## Web Dashboard

Real-time browser-based monitoring for Clove agents.

```
Browser (localhost:8000) → WebSocket → ws_proxy.py → Unix Socket → Kernel
```

**Quick Start:**
```bash
# Terminal 1: Kernel
./build/clove_kernel

# Terminal 2: WebSocket proxy
python3 agents/dashboard/ws_proxy.py

# Terminal 3: HTTP server
cd agents/dashboard && python3 -m http.server 8000

# Open: http://localhost:8000
```

**Features:**
- Live agent monitoring with real-time status updates
- Spawn/kill agents directly from the UI
- Process hierarchy visualization
- System resource stats (CPU, memory, agents)
- Auto-reconnect on connection loss

<!-- TODO: Add dashboard screenshot here -->
<!-- ![Dashboard Screenshot](docs/images/dashboard.png) -->

## Agentic Loop Framework

LLM-powered autonomous agent that can execute commands, read/write files, and reason iteratively - similar to Claude Code.

```python
from agentic import run_task, AgenticLoop

# Quick usage
result = run_task("Create a hello.py and run it")

# With more control
with CloveClient() as client:
    loop = AgenticLoop(client, max_iterations=20)
    result = loop.run("List all Python files and count them")
```

**Features:** Iterative task execution, built-in tools (exec, read_file, write_file, done), conversation history, extensible tool system.

## Cloud Deployment (CLI)

Deploy Clove kernels anywhere with a single command.

```bash
# Install CLI
pip install -e cli/

# Deploy to Docker
$ clove deploy docker --name dev-kernel
Creating Clove kernel container...
  Machine ID: docker-dev-kernel-a1b2
  Status: Running ✓

# Deploy to AWS
$ clove deploy aws --region us-east-1
Provisioning AWS EC2 instance...
  Machine ID: aws-i-0abc123-us-east-1
  SSH: ssh -i ~/.ssh/clove.pem ubuntu@54.123.45.67

# Deploy to GCP
$ clove deploy gcp --zone us-central1-a
Provisioning GCP Compute instance...
  Machine ID: gcp-clove-kernel-us-central1

# Check fleet status
$ clove status
Connected Kernels: 3
Active Agents: 5

# Run agent remotely
$ clove agent run my_agent.py --machine docker-dev-kernel-a1b2
```

**CLI Commands:**
| Command | Description |
|---------|-------------|
| `clove deploy docker` | Deploy to local Docker |
| `clove deploy aws` | Deploy to AWS EC2 |
| `clove deploy gcp` | Deploy to GCP Compute |
| `clove status` | Show fleet status |
| `clove machines list` | List all machines |
| `clove agent run <script>` | Run agent on machine |
| `clove tokens create` | Create auth tokens |

## Remote Connectivity

Cloud agents connect to your local kernel through a relay server:

```
┌─────────────────────────────────────────────────────────────────┐
│                         YOUR TERMINAL                            │
│  $ clove deploy aws    $ clove status    $ clove agent run      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RELAY SERVER (Cloud/Self-Hosted)              │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐            │
│   │  REST API  │    │  WebSocket │    │   Fleet    │            │
│   │ (CLI mgmt) │    │    Hub     │    │  Manager   │            │
│   └────────────┘    └────────────┘    └────────────┘            │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  AWS EC2        │ │  GCP Compute    │ │  Docker Local   │
│  Clove Kernel   │ │  Clove Kernel   │ │  Clove Kernel   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

**Start relay server:**
```bash
cd relay && python3 relay_server.py --dev
```

## Future Directions

Clove's sandbox architecture opens up possibilities beyond just running agents safely.

### Agent & Workflow Benchmarking

The isolated, resource-controlled environment makes Clove ideal for **reproducible agent benchmarks**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Benchmark Controller                          │
├─────────────────────────────────────────────────────────────────┤
│  Test Suite: "Code Generation Tasks v1.0"                        │
│  ├─ Task 1: Parse JSON and extract fields                       │
│  ├─ Task 2: Implement binary search                             │
│  ├─ Task 3: Debug failing test case                             │
│  └─ Task 4: Refactor legacy function                            │
├─────────────────────────────────────────────────────────────────┤
│                    Clove Kernel                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Agent A      │  │ Agent B      │  │ Agent C      │          │
│  │ (GPT-4)      │  │ (Claude)     │  │ (Gemini)     │          │
│  │ Memory: 256M │  │ Memory: 256M │  │ Memory: 256M │          │
│  │ CPU: 50%     │  │ CPU: 50%     │  │ CPU: 50%     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  Metrics Collected:                                              │
│  - Task completion rate        - Token usage                    │
│  - Time to completion          - Memory peak                    │
│  - Error recovery attempts     - Tool call patterns             │
│  - Multi-step reasoning depth  - Cost per task                  │
└─────────────────────────────────────────────────────────────────┘
```

**Why Clove for benchmarks:**
- **Identical conditions** - Same resource limits, same sandboxing for all agents
- **No interference** - Agents can't affect each other's performance
- **Reproducible** - Controlled environment ensures consistent results
- **Real metrics** - Kernel-level resource tracking (not just token counts)
- **Failure handling** - Measure how agents recover from crashes/timeouts

### World Simulation via Sandbox

The sandbox primitives can be extended to create **controlled virtual worlds** for agent testing:

```
┌─────────────────────────────────────────────────────────────────┐
│                      World Definition                            │
│  {                                                               │
│    "name": "e-commerce-sandbox",                                │
│    "filesystem": {                                              │
│      "/app": "simulated web application",                       │
│      "/db": "mock database with test data",                     │
│      "/logs": "writable log directory"                          │
│    },                                                           │
│    "network": {                                                 │
│      "allowed_hosts": ["api.stripe.test", "db.local"],         │
│      "latency_ms": 50,                                          │
│      "failure_rate": 0.01                                       │
│    },                                                           │
│    "time": {                                                    │
│      "acceleration": 10,                                        │
│      "start": "2024-01-01T00:00:00Z"                           │
│    },                                                           │
│    "events": [                                                  │
│      {"at": "+1h", "type": "db_failure", "duration": "5m"},    │
│      {"at": "+2h", "type": "traffic_spike", "multiplier": 10}  │
│    ]                                                            │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Clove World Instance                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Simulated Filesystem    │  Simulated Network              │ │
│  │  - Virtual /app          │  - Mock HTTP responses          │ │
│  │  - Seeded /db            │  - Injected failures            │ │
│  │  - Monitored writes      │  - Latency simulation           │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Agent Under Test                                          │ │
│  │  Task: "Monitor the e-commerce app, detect and fix issues" │ │
│  │  Tools: read, write, exec, http                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Evaluation Criteria                                       │ │
│  │  - Did agent detect db_failure event?                      │ │
│  │  - Did agent scale appropriately for traffic_spike?        │ │
│  │  - Did agent maintain data integrity?                      │ │
│  │  - Resource efficiency during incident response            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**World formation capabilities:**
- **Filesystem virtualization** - Mount custom directory trees, inject files, track modifications
- **Network simulation** - Mock APIs, inject latency/failures, restrict connectivity
- **Time manipulation** - Accelerate time for long-running tests, schedule events
- **Event injection** - Trigger failures, load spikes, data corruption at specific times
- **State snapshots** - Save/restore world state for reproducible testing

**Use cases:**
- Test SRE agents against simulated outages
- Evaluate coding agents in realistic project environments
- Benchmark multi-agent collaboration in shared worlds
- Train agents on edge cases without risking production systems

### Roadmap

| Phase | Feature | Description |
|-------|---------|-------------|
| Current | Agent Runtime | OS-level isolation, permissions, framework adapters |
| Next | Benchmark Framework | Standardized task suites, metrics collection, comparison tools |
| Future | World Simulation | Filesystem virtualization, network mocking, event injection |
| Vision | Agent Gymnasium | Library of worlds for training and evaluating autonomous agents |

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url> Clove
cd Clove

# Install vcpkg if you don't have it
git clone https://github.com/Microsoft/vcpkg.git ~/vcpkg
~/vcpkg/bootstrap-vcpkg.sh
export VCPKG_ROOT="$HOME/vcpkg"
```

### 2. Install Dependencies

```bash
# System dependencies
sudo apt install -y build-essential cmake pkg-config libssl-dev python3 python3-pip python3-venv

# Create and activate virtual environment
python3 -m venv clove_env
source clove_env/bin/activate

# Python dependencies (for LLM service)
pip install google-genai
```

### 3. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your Gemini API key
```

### 4. Build and Run

```bash
mkdir -p build && cd build
cmake ..
make -j$(nproc)
./clove_kernel
```

## Python SDK

```python
from clove import CloveClient

with CloveClient() as client:
    # LLM query
    result = client.think("What is 2+2?")
    print(result['content'])

    # Spawn sandboxed agent
    client.spawn(
        name="worker",
        script="/path/to/agent.py",
        sandboxed=True,
        limits={"memory": 256*1024*1024}
    )

    # Execute with permission checks
    client.exec("ls -la /tmp")

    # HTTP with domain restrictions
    client.http("https://api.github.com/users/octocat")

    # System metrics (CPU, memory, disk, network)
    metrics = client.get_system_metrics()
    print(f"CPU: {metrics['metrics']['cpu']['percent']}%")

    # Agent metrics
    agents = client.get_all_agent_metrics()
    for agent in agents['agents']:
        print(f"{agent['name']}: {agent['process']['cpu']['percent']}%")
```

## Permission System

| Level | Description |
|-------|-------------|
| `unrestricted` | Full access (dangerous!) |
| `standard` | Default safe restrictions |
| `sandboxed` | Strict restrictions, limited paths |
| `readonly` | Can only read, no writes or execution |
| `minimal` | Almost no permissions |

Features:
- **Path validation** - Glob patterns for allowed/blocked paths
- **Command filtering** - Block dangerous commands (rm -rf, sudo, etc.)
- **Domain whitelist** - HTTP requests limited to approved domains
- **LLM quotas** - Token and call limits per agent

## Framework Integration

Clove adapters for existing frameworks - all operations go through the permission system:

- **LangChain** - `CloveToolkit` provides tools for any LangChain agent
- **CrewAI** - `CloveCrewAgent` factory with pre-built agent types
- **AutoGen** - `CloveAssistant` and `CloveUserProxy` for multi-agent chat
- **MCP** - Claude Desktop integration via Model Context Protocol

## Multi-Agent Benchmark: Clove vs LangGraph

Compare Clove's multi-agent architecture against LangGraph with a real-world example.

```bash
# Run the benchmark
cd worlds/examples/research_team
python3 benchmark.py --iterations 3
```

**The Example:** A research team with 3 agents (Coordinator, Researcher, Writer) that collaborate to produce a report on a given topic.

| Implementation | Description |
|----------------|-------------|
| `langgraph_version.py` | LangGraph StateGraph - all agents in one process |
| `clove_version.py` | Clove single-process - kernel-mediated LLM calls |
| `clove_multiprocess.py` | Clove multi-process - real process isolation with IPC |

**Key Advantages of Clove Multi-Process:**
- **Crash Isolation**: If one agent crashes, others continue unaffected
- **Resource Limits**: Each agent can have memory/CPU caps (cgroups)
- **Security**: Agents can be sandboxed with Linux namespaces
- **Scalability**: Agents can run on different machines via relay

See [worlds/examples/research_team/README.md](worlds/examples/research_team/README.md) for full details.

## Syscall Reference

| Opcode | Name | Description |
|--------|------|-------------|
| 0x00 | SYS_NOOP | Echo test |
| 0x01 | SYS_THINK | LLM query (multimodal) |
| 0x02 | SYS_READ | Read file |
| 0x03 | SYS_WRITE | Write file |
| 0x04 | SYS_EXEC | Execute command |
| 0x10 | SYS_SPAWN | Spawn sandboxed agent |
| 0x11 | SYS_KILL | Kill agent |
| 0x12 | SYS_LIST | List agents |
| 0x20-0x23 | IPC | Inter-agent messaging |
| 0x30-0x33 | STATE | Key-value state store |
| 0x40-0x41 | PERMS | Permission management |
| 0x50 | SYS_HTTP | HTTP request |
| 0x60-0x63 | EVENTS | Pub/sub event system |
| 0xC0-0xC3 | METRICS | System/agent metrics |
| 0xFF | SYS_EXIT | Disconnect |

## Project Structure

```
Clove/
├── src/
│   ├── main.cpp
│   ├── kernel/           # Kernel, reactor, LLM client, permissions
│   │   └── metrics/      # System and agent metrics collection
│   ├── ipc/              # Protocol and Unix socket server
│   ├── runtime/          # Sandbox (namespaces/cgroups) and agent lifecycle
│   └── util/             # Logging utilities
├── agents/
│   ├── python_sdk/       # Python client library + agentic loop + fleet client
│   ├── dashboard/        # Web monitoring UI + WebSocket proxy
│   ├── llm_service/      # LLM subprocess (google-genai)
│   ├── mcp/              # MCP server for Claude Desktop
│   ├── adapters/         # LangChain, CrewAI, AutoGen adapters
│   └── examples/         # Demo agents
├── cli/                  # Clove CLI tool
│   ├── clove.py          # Main entry point
│   ├── config.py         # Configuration management
│   ├── relay_api.py      # Relay REST API client
│   └── commands/         # CLI commands (deploy, status, machines, agent, tokens)
├── relay/                # Relay server for remote connectivity
│   ├── relay_server.py   # WebSocket relay server
│   ├── api.py            # REST API endpoints
│   ├── fleet.py          # Fleet management
│   └── tokens.py         # Token persistence
├── deploy/               # Deployment assets
│   ├── docker/           # Dockerfile, docker-compose.yml
│   ├── terraform/        # AWS and GCP Terraform modules
│   └── systemd/          # Systemd service files
├── demos/                # Demo scripts showcasing Clove features
├── worlds/               # World simulations and examples
│   └── examples/         # Multi-agent examples and benchmarks
│       └── research_team/  # Clove vs LangGraph comparison
├── benchmarks/           # Benchmark runners and configurations
├── test_suite/           # Test suite for all components
├── docs/                 # Documentation
├── build/
├── CMakeLists.txt
├── vcpkg.json
└── STATUS.md
```

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation and first steps |
| [Architecture](docs/architecture.md) | System design and internals |
| [Syscalls Reference](docs/syscalls.md) | All available syscalls |
| [CLI Reference](cli/README.md) | Fleet management CLI |
| [Python SDK](agents/python_sdk/README.md) | SDK usage and API |
| [Examples](agents/examples/README.md) | Demo agents and use cases |
| [Multi-Agent Benchmark](worlds/examples/research_team/README.md) | Clove vs LangGraph comparison |

## Requirements

- Linux (Ubuntu 22.04+ / Debian 12+)
- GCC 11+ with C++23 support
- CMake 3.20+
- Python 3.10+
- Root for full sandbox isolation (optional)

## License

MIT License

---

Built with C++23, powered by Google Gemini.
