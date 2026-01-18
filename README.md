# AgentOS

A microkernel operating system for AI agents. Run multiple autonomous agents as isolated processes with OS-level guarantees.

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

## Future Directions

AgentOS's sandbox architecture opens up possibilities beyond just running agents safely.

### Agent & Workflow Benchmarking

The isolated, resource-controlled environment makes AgentOS ideal for **reproducible agent benchmarks**:

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
│                    AgentOS Kernel                                │
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

**Why AgentOS for benchmarks:**
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
│                    AgentOS World Instance                        │
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
cp .env.example .env
# Edit .env and add your Gemini API key
```

### 4. Build and Run

```bash
mkdir -p build && cd build
cmake ..
make -j$(nproc)
./agentos_kernel
```

## Python SDK

```python
from agentos import AgentOSClient

with AgentOSClient() as client:
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

AgentOS adapters for existing frameworks - all operations go through the permission system:

- **LangChain** - `AgentOSToolkit` provides tools for any LangChain agent
- **CrewAI** - `AgentOSCrewAgent` factory with pre-built agent types
- **AutoGen** - `AgentOSAssistant` and `AgentOSUserProxy` for multi-agent chat
- **MCP** - Claude Desktop integration via Model Context Protocol

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
| 0x40-0x41 | PERMS | Permission management |
| 0x50 | SYS_HTTP | HTTP request |
| 0xFF | SYS_EXIT | Disconnect |

## Project Structure

```
AgentOS/
├── src/
│   ├── main.cpp
│   ├── kernel/           # Kernel, reactor, LLM client, permissions
│   ├── ipc/              # Protocol and Unix socket server
│   ├── runtime/          # Sandbox (namespaces/cgroups) and agent lifecycle
│   └── util/             # Logging utilities
├── agents/
│   ├── python_sdk/       # Python client library
│   ├── llm_service/      # LLM subprocess (google-genai)
│   ├── mcp/              # MCP server for Claude Desktop
│   ├── adapters/         # LangChain, CrewAI, AutoGen adapters
│   └── examples/         # Demo agents
├── build/
├── CMakeLists.txt
├── vcpkg.json
└── STATUS.md
```

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
