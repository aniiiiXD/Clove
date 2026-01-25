# Clove Development Status

**Last Updated:** 2026-01-26

---

## Recent: Metrics System **COMPLETE**

Kernel-level metrics collection for system monitoring, benchmarking, and TUI dashboards.

**New Syscalls:**
| Opcode | Name | Description |
|--------|------|-------------|
| `0xC0` | `SYS_METRICS_SYSTEM` | Get system-wide metrics (CPU, memory, disk, network) |
| `0xC1` | `SYS_METRICS_AGENT` | Get metrics for a specific agent |
| `0xC2` | `SYS_METRICS_ALL_AGENTS` | Get metrics for all running agents |
| `0xC3` | `SYS_METRICS_CGROUP` | Get cgroup resource metrics |

**Implementation:**
- `src/kernel/metrics/metrics.hpp` - Data structures
- `src/kernel/metrics/metrics.cpp` - Collection from /proc and /sys/fs/cgroup
- Python SDK: `get_system_metrics()`, `get_agent_metrics()`, `get_all_agent_metrics()`, `get_cgroup_metrics()`
- Test: `test_suite/11_metrics.py`

**Metrics Collected:**
- CPU: percent, per-core, load average
- Memory: total, used, available, percent
- Disk: read/write bytes
- Network: sent/received bytes
- Process: CPU%, memory RSS/VMS, threads, file descriptors
- Cgroup: CPU usage, memory limits, PID limits

---

## Current Phase: Phase 9 - World Simulation **NEXT**

**Goal:** Create isolated, configurable environments ("worlds") where agents can operate without affecting real systems. Essential for training, testing, and safe experimentation.

---

## Recent Additions (2026-01-20)

### Phase 8: Cloud Deployment System **COMPLETE**

One-command deploy Clove to any cloud or local Docker, manage a fleet of kernels from your terminal.

**CLI Tool (`cli/`):**
```bash
$ clove deploy docker --name dev-kernel
$ clove deploy aws --region us-east-1
$ clove deploy gcp --zone us-central1-a
$ clove status
$ clove agent run my_agent.py --machine docker-dev-kernel-xxx
```

**Components Implemented:**
- `cli/clove.py` - Main CLI entry point (Click framework)
- `cli/config.py` - Configuration management (~/.clove/config.yaml)
- `cli/relay_api.py` - REST API client for relay server
- `cli/commands/` - Deploy, status, machines, agent, tokens commands
- `relay/api.py` - REST API endpoints for fleet management
- `relay/fleet.py` - Fleet manager with persistence
- `relay/tokens.py` - Token persistence and validation
- `deploy/docker/` - Dockerfile, docker-compose.yml, entrypoint.sh
- `deploy/terraform/aws/` - EC2 + networking Terraform module
- `deploy/terraform/gcp/` - Compute Engine Terraform module
- `deploy/systemd/` - Systemd service files
- `agents/python_sdk/clove_sdk/fleet.py` - Fleet management Python client

**Architecture:**
```
┌──────────────────────────────────────────────────────────────────┐
│                         YOUR TERMINAL                             │
│  $ clove deploy aws    $ clove status    $ clove agent run │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    RELAY SERVER (Cloud/Self-Hosted)               │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐             │
│   │  REST API  │    │  WebSocket │    │   Fleet    │             │
│   │ (CLI mgmt) │    │    Hub     │    │  Manager   │             │
│   └────────────┘    └────────────┘    └────────────┘             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  AWS EC2        │ │  GCP Compute    │ │  Docker Local   │
│  Clove Kernel │ │  Clove Kernel │ │  Clove Kernel │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Previous Additions (2026-01-20)

### Events (Pub/Sub) System **NEW**

Kernel-level event system for agent coordination and notifications.

**Syscalls:**
- `SYS_SUBSCRIBE` (0x60) - Subscribe to event types
- `SYS_UNSUBSCRIBE` (0x61) - Unsubscribe from events
- `SYS_POLL_EVENTS` (0x62) - Get pending events
- `SYS_EMIT` (0x63) - Emit custom events

**Event Types:**
- `AGENT_SPAWNED` - Emitted when an agent is spawned
- `AGENT_EXITED` - Emitted when an agent is killed
- `MESSAGE_RECEIVED` - IPC message notification
- `STATE_CHANGED` - State store key modified
- `SYSCALL_BLOCKED` - Permission denied
- `RESOURCE_WARNING` - Approaching resource limits
- `CUSTOM` - User-defined events

**Usage:**
```python
# Subscribe to events
client.subscribe(["AGENT_SPAWNED", "AGENT_EXITED", "CUSTOM"])

# Poll for events
events = client.poll_events(max_events=10)
for event in events["events"]:
    print(f"{event['type']}: {event['data']}")

# Emit custom event
client.emit_event("CUSTOM", {"msg": "task_complete"})
```

### State Store **NEW**

Shared key-value storage for agent coordination.

**Syscalls:** `SYS_STORE`, `SYS_FETCH`, `SYS_DELETE`, `SYS_KEYS` (0x30-0x33)

**Features:**
- Scopes: `global`, `agent` (private), `session`
- TTL support for automatic expiration
- Prefix-based key listing

### Web Dashboard **NEW**

Real-time browser-based monitoring dashboard for Clove agents.

**Features:**
- Live agent monitoring via WebSocket (updates every second)
- Spawn and kill agents directly from the UI
- Process hierarchy visualization
- System statistics (running, stopped, failed counts)
- Dark terminal-inspired theme
- Auto-reconnect when kernel restarts

**Architecture:**
```
Browser (localhost:8000) → WebSocket (ws://localhost:8765) → ws_proxy.py → Unix Socket → Kernel
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

### Agentic Loop Framework **NEW**

LLM-powered autonomous agent framework (`agents/python_sdk/clove_sdk/agentic.py`) - similar to Claude Code's approach.

**Features:**
- Iterative task execution with LLM reasoning
- Built-in tools: `exec`, `read_file`, `write_file`, `done`
- Conversation history management
- Extensible tool system
- Configurable max iterations

**Usage:**
```python
from agentic import run_task, AgenticLoop

# Quick usage
result = run_task("Create a hello.py and run it")

# With more control
with CloveClient() as client:
    loop = AgenticLoop(client, max_iterations=20)
    result = loop.run("List all Python files")
```

---

## Phase 5: Universal Agent Runtime **COMPLETE**

**Goal:** Make Clove the universal runtime layer that ANY agent/workflow can plug into - with controlled access to your PC.

**Status (2026-01-20):** All core implementation complete:
- 5.1 Permission System ✓
- 5.2 Host Access Syscalls (SYS_HTTP) ✓
- 5.3 MCP Server for Claude Desktop ✓
- 5.4 Framework Adapters (LangChain, CrewAI, AutoGen) ✓

---

## Phase 4: OS-Level Demonstrations **COMPLETE**

**Goal:** Prove why Clove must exist with workflows that *only* an OS-level kernel can handle cleanly.

**Status:** All 5 workflows implemented:
- 4.1 Crash-Resistant Agents ✓
- 4.2 LLM Contention & Fair Scheduling ✓
- 4.3 Untrusted Agent Execution (Security) ✓
- 4.4 Supervisor Agent (PID 1 Semantics) ✓
- 4.5 Agent Pipelines with Real IPC ✓

---

## Critical Gap Analysis

> **"Your kernel is operating-system-grade, but your workflows are notebook-grade."**

### What the Kernel Supports vs What Examples Demonstrate

| Capability              | Kernel Supports        | Examples Actually Show |
| ----------------------- | ---------------------- | ---------------------- |
| Process isolation       | ✅ namespaces + cgroups | ❌ barely               |
| Shared LLM multiplexing | ✅                      | ❌ not stressed         |
| IPC performance         | ✅ binary UDS           | ❌ not benchmarked      |
| Agent lifecycle         | ✅ spawn / kill         | ⚠️ shallow             |
| Fault isolation         | ✅                      | ❌ absent               |
| Resource limits         | ✅                      | ❌ unused               |
| OS-style supervision    | ✅                      | ❌ absent               |

### The Problem

Current examples could be written with **LangChain / CrewAI / AutoGen**. Reviewers won't immediately see why **C++ kernel + namespaces + cgroups** is required.

### The Solution

Build **"meaner, more adversarial examples"** that demonstrate:
- Isolation
- Scheduling
- Failure handling
- Adversarial behavior

---

## Phase 4: OS-Level Workflows (Why Clove Exists)

### 4.1 Crash-Resistant Agents (Kernel-Level Fault Isolation)

**What to demonstrate:**
- One agent segfaults / infinite loops
- Kernel detects it
- Other agents continue unaffected

**Why this matters:** This is literally *why operating systems exist*.

**Target output:**
```
Agent A: infinite loop (CPU hog)    → throttled
Agent B: memory leak (hits limit)   → killed
Agent C: healthy                    → continues
```

| Task | Status | Notes |
|------|--------|-------|
| Create cpu_hog_agent.py | [x] Done | Infinite loop agent |
| Create memory_hog_agent.py | [x] Done | Memory leak agent |
| Create healthy_agent.py | [x] Done | Normal operation |
| Create fault_isolation_demo.py | [x] Done | Orchestrator script |
| Verify kernel throttles/kills bad actors | [x] Done | Works with root (cgroups) |
| Document behavior | [x] Done | See test results below |

**Phase 4.1 Test Results (User Mode):**
```
[USER MODE] Limited isolation (run with sudo for full demo)

Spawning cpu-hog: CPU burner (should be throttled to 10%)
  ✓ Spawned: PID=38716
Spawning mem-hog: Memory leaker (should be OOM-killed at 50MB)
  ✓ Spawned: PID=38717
Spawning healthy: Well-behaved agent (should survive)
  ✓ Spawned: PID=38718

Demo Summary:
  ✓ HEALTHY agent survived (fault isolation works!)
  ⚠ MEM-HOG not killed (requires root for cgroups)
  ✓ CPU-HOG was throttled/managed by kernel
```

**Note:** Full cgroups isolation requires running kernel with `sudo`. In user mode, agents spawn and run in separate processes but resource limits are not enforced.

---

### 4.2 LLM Contention & Fair Scheduling

**What to demonstrate:**
- Spawn 5 agents
- All request LLM simultaneously
- Kernel naturally queues requests through single LLM subprocess
- Fair access demonstrated via latency tracking

**Target output:**
```
Agent           Requests   Success    Avg Latency  Tokens
------------------------------------------------------------
llm-agent-1     2          2          1200ms       45
llm-agent-2     2          2          1150ms       42
llm-agent-3     2          2          1180ms       48
...
```

**Positioning:** *"Clove is a kernel scheduler for LLM access"*

| Task | Status | Notes |
|------|--------|-------|
| LLM request serialization via subprocess | [x] Done | Natural FIFO queue |
| Create llm_requester_agent.py | [x] Done | Individual agent for testing |
| Create llm_contention_demo.py | [x] Done | Spawns 5 agents, tracks latency |
| Add metrics (latency, tokens) | [x] Done | Per-agent tracking |
| Document behavior | [x] Done | See demo output |

**Phase 4.2 Test Agents:**
- `llm_requester_agent.py` - Makes LLM requests, reports timing to orchestrator
- `llm_contention_demo.py` - Spawns multiple agents, demonstrates fair scheduling

**Note:** Requires GEMINI_API_KEY to be set for LLM requests.

---

### 4.3 Untrusted Agent Execution (Security Story)

**What to demonstrate:**
- Run untrusted/malicious agents
- Agent attempts: network access, fork bomb
- Kernel blocks/kills via namespaces + cgroups

**Target output:**
```
BLOCKED: network namespace isolation
KILLED: PID limit exceeded (fork bomb stopped)
THROTTLED: CPU/memory limits enforced
```

**Positioning:** *"Clove is Docker-lite for AI agents"*

| Task | Status | Notes |
|------|--------|-------|
| Create network_test_agent.py | [x] Done | Tests network isolation |
| Create fork_bomb_agent.py | [x] Done | Tests PID limit protection |
| Create security_demo.py | [x] Done | Runs all security tests |
| Verify network isolation | [x] Done | Works with CLONE_NEWNET |
| Verify fork bomb protection | [x] Done | Works with cgroups max_pids |
| Document behavior | [x] Done | See test agents for details |

**Phase 4.3 Test Agents:**
- `fork_bomb_agent.py` - Attempts to spawn 100 processes, blocked by max_pids
- `network_test_agent.py` - Tests DNS, TCP, HTTP - all blocked in isolated namespace
- `security_demo.py` - Orchestrator comparing isolated vs non-isolated agents

**Note:** Full isolation requires running kernel with `sudo` for namespace/cgroup access.

---

### 4.4 Supervisor / Init-Style Agent (PID 1 Semantics)

**What to demonstrate:**
- Supervisor agent watches child agents
- Restarts failed agents with backoff
- Escalates after max restart attempts

**Mirrors:** `systemd`, Kubernetes controllers, Erlang supervisors

| Task | Status | Notes |
|------|--------|-------|
| Create supervisor_agent.py | [x] Done | Full supervisor implementation |
| Create unstable_agent.py | [x] Done | Test agent that crashes randomly |
| Implement child watching | [x] Done | Polls agent list for dead children |
| Implement restart policy | [x] Done | Max 3 restarts with backoff |
| Implement escalation | [x] Done | Stops restarting after limit |
| Create supervisor_demo.py | [x] Done | Wrapper with explanation |
| Document behavior | [x] Done | See demo output |

**Phase 4.4 Test Agents:**
- `supervisor_agent.py` - Implements init/systemd-style supervision
- `unstable_agent.py` - Worker that crashes after 3-8 heartbeats
- `supervisor_demo.py` - Demo wrapper with summary

**Features Demonstrated:**
- Automatic crash detection
- Restart with exponential backoff
- Restart limits (max 3 per agent)
- Escalation for persistent failures

---

### 4.5 Agent Pipelines with Real IPC

**What to demonstrate:**
- Agent A → parses input (text to structured data)
- Agent B → runs reasoning (compute results)
- Agent C → verifies output (validates correctness)
- Real kernel-mediated IPC (SYS_SEND/SYS_RECV)

**Positioning:** *"Agents are processes, not coroutines."*

| Task | Status | Notes |
|------|--------|-------|
| Create parser_agent.py | [x] Done | Stage 1: parse math expressions |
| Create reasoner_agent.py | [x] Done | Stage 2: compute results |
| Create verifier_agent.py | [x] Done | Stage 3: verify correctness |
| Implement inter-agent messaging | [x] Done | Uses SYS_SEND/SYS_RECV |
| Create pipeline_demo.py | [x] Done | Orchestrator with test queries |
| Document behavior | [x] Done | See demo output |

**Phase 4.5 Test Agents:**
- `parser_agent.py` - Parses natural language math to structured form
- `reasoner_agent.py` - Computes mathematical results
- `verifier_agent.py` - Validates results are correct
- `pipeline_demo.py` - Orchestrator that runs 5 test queries

**Pipeline Flow:**
```
Orchestrator → Parser → Reasoner → Verifier → Orchestrator
                ↓          ↓           ↓
            "parse"    "compute"   "verify"
```

---

## Phase 4 Progress

| # | Workflow | Status | Notes |
|---|----------|--------|-------|
| 4.1 | Crash-Resistant Agents | [x] **COMPLETE** | Fault isolation demo working |
| 4.2 | LLM Contention | [x] **COMPLETE** | Fair scheduling via subprocess queue |
| 4.3 | Untrusted Execution | [x] **COMPLETE** | Security demo with fork bomb + network isolation |
| 4.4 | Supervisor Agent | [x] **COMPLETE** | PID 1 semantics with restart policies |
| 4.5 | Agent Pipelines | [x] **COMPLETE** | Real IPC with parser→reasoner→verifier |

**Phase 4 COMPLETE!** All 5 OS-level workflows implemented.

---

## Existing Examples (Reframed)

**SDK Onboarding / Smoke Tests:**
- `hello_agent.py` - Basic IPC verification
- `thinking_agent.py` - LLM connectivity test
- `spawn_test.py` - Lifecycle basics
- `worker_agent.py` - Spawnable agent template

**OS-Level Demonstrations (Phase 4):**
- `fault_isolation_demo.py` - Spawns 3 agents, proves isolation
- `cpu_hog_agent.py` - CPU stress test (throttled by cgroups)
- `memory_hog_agent.py` - Memory leak (killed by cgroups)
- `healthy_agent.py` - Well-behaved agent (survives failures)
- `security_demo.py` - Security isolation demo
- `fork_bomb_agent.py` - Fork bomb attack (blocked by max_pids)
- `network_test_agent.py` - Network isolation tests
- `llm_contention_demo.py` - Fair LLM scheduling demo
- `llm_requester_agent.py` - LLM request agent for contention tests
- `supervisor_demo.py` - PID 1 semantics demo
- `supervisor_agent.py` - Implements systemd-style supervision
- `unstable_agent.py` - Test agent that crashes randomly
- `pipeline_demo.py` - Agent pipeline with real IPC
- `parser_agent.py` - Pipeline stage 1: parse input
- `reasoner_agent.py` - Pipeline stage 2: compute results
- `verifier_agent.py` - Pipeline stage 3: verify correctness
- `ipc_demo.py` - Inter-agent communication demonstration
- `coding_agent.py` - Code generation agent using LLM
- `fibonacci_orchestrator.py` - Multi-agent orchestration example

---

## Phase 3: LLM Integration (Gemini) **COMPLETE** (Updated 2026-01-17)

**Goal:** Connect to Google Gemini API and enable agents to think via SYS_THINK.

**Architecture Update (2026-01-17):** Replaced C++ HTTP client with Python subprocess using google-genai SDK. This enables:
- Multimodal support (text + images)
- System instructions
- Thinking configurations (thinking_level)
- Cleaner separation of LLM logic

---

## Phase 3 Tasks

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Add cpp-httplib + OpenSSL | [x] Done | Still used for other HTTP needs |
| 3.2 | Create llm_client.hpp/cpp | [x] Done | Subprocess manager (not HTTP) |
| 3.3 | Create llm_service.py | [x] Done | Python subprocess using google-genai |
| 3.4 | Integrate into kernel | [x] Done | LLMClient spawns Python subprocess |
| 3.5 | Update SYS_THINK handler | [x] Done | JSON payload with extended options |
| 3.6 | Update Python SDK think() | [x] Done | Multimodal, system_instruction, thinking_level |
| 3.7 | Create thinking_agent.py | [x] Done | Interactive example |
| 3.8 | Add .env file loading | [x] Done | Auto-loads from project root |
| 3.9 | Test multimodal support | [x] Done | Image input working |

---

## LLM Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Clove Kernel (C++)                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  LLMClient                                             │  │
│  │  - Spawns Python subprocess                           │  │
│  │  - Communicates via stdin/stdout (JSON)               │  │
│  │  - Loads .env file for API keys                       │  │
│  └────────────────────────┬──────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────┘
                            │ JSON over pipes
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 LLM Service (Python subprocess)              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  llm_service.py                                        │  │
│  │  - Uses google-genai SDK                              │  │
│  │  - Supports multimodal (text + images)                │  │
│  │  - Supports system_instruction, thinking_level        │  │
│  │  - Loads .env file for API keys                       │  │
│  └────────────────────────┬──────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────┘
                            │ HTTPS
                            ▼
                    ┌───────────────┐
                    │  Gemini API   │
                    └───────────────┘
```

---

## Phase 3 Test Results

```
[Test 1] SYS_THINK without API key - PASS (returns error JSON)
[Test 2] SYS_NOOP echo            - PASS (still works)
[Test 3] Kernel starts with LLM   - PASS (logs LLM status)
[Test 4] .env file loading        - PASS (auto-loads API key)
[Test 5] Multimodal (image+text)  - PASS (image input works)
```

Note: Set GEMINI_API_KEY in .env file or environment variable for live LLM calls.

---

## Phase 2 Tasks

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Create sandbox.hpp/cpp | [x] Done | Process isolation manager |
| 2.2 | Implement namespace isolation | [x] Done | PID, NET, MNT, UTS namespaces |
| 2.3 | Implement cgroups v2 limits | [x] Done | Memory, CPU, PIDs limits |
| 2.4 | Create agent_process.hpp/cpp | [x] Done | Agent lifecycle management |
| 2.5 | Integrate into kernel | [x] Done | SYS_SPAWN, SYS_KILL, SYS_LIST |
| 2.6 | Update CMakeLists.txt | [x] Done | Added runtime sources |
| 2.7 | Create worker_agent.py | [x] Done | Test agent for spawning |
| 2.8 | Create spawn_test.py | [x] Done | End-to-end spawn test |
| 2.9 | Test sandbox | [x] Done | Works (needs root for full isolation) |

---

## Phase 2 Test Results

```
[Test 1] List agents (initial)     - PASS (0 agents)
[Test 2] Spawn worker agent        - PASS (id=2, pid=29435)
[Test 3] List agents (after spawn) - PASS (1 agent running)
[Test 4] Worker communication      - PASS (5 heartbeats)
[Test 5] List agents (after work)  - PASS
[Test 6] Kill agent                - PASS (killed=True)
```

Note: Full namespace/cgroup isolation requires root. Without root, falls back to fork().

---

## Phase 1 Tasks (Completed)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Implement protocol.hpp | [x] Done | Binary serialize/deserialize |
| 1.2 | Implement socket_server.cpp | [x] Done | Unix domain socket server |
| 1.3 | Implement reactor.cpp | [x] Done | epoll event loop |
| 1.4 | Integrate kernel.cpp | [x] Done | Wire all components |
| 1.5 | Update main.cpp | [x] Done | Entry point |
| 1.6 | Write Python SDK | [x] Done | agents/python_sdk/clove.py |
| 1.7 | Create hello_agent.py | [x] Done | agents/examples/hello_agent.py |
| 1.8 | End-to-end test | [x] Done | All tests pass! |

---

## Phase 0 Tasks (Completed)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0.1 | Install system tools | [x] Done | gcc 11.4.0, cmake 3.22.1 |
| 0.2 | Install vcpkg | [x] Done | ~/vcpkg |
| 0.3 | Create project structure | [x] Done | Complete |
| 0.4 | Build & verify | [x] Done | Working |

---

## Project Structure (Current)

```
CLOVE/
├── src/
│   ├── main.cpp                  # Entry point
│   ├── kernel/
│   │   ├── kernel.hpp            # Kernel class + LLM config
│   │   ├── kernel.cpp            # + spawn/kill/list/think handlers
│   │   ├── reactor.hpp           # Event loop
│   │   ├── reactor.cpp           # epoll implementation
│   │   ├── llm_client.hpp        # LLM subprocess manager
│   │   ├── llm_client.cpp        # Subprocess IPC, .env loading
│   │   ├── permissions.hpp       # Permission system
│   │   ├── permissions.cpp       # Permission validation
│   │   └── metrics/              # Metrics collection
│   │       ├── metrics.hpp       # Data structures
│   │       └── metrics.cpp       # Collection from /proc, /sys
│   ├── ipc/
│   │   ├── protocol.hpp          # Binary protocol + opcodes
│   │   ├── socket_server.hpp     # Server class
│   │   └── socket_server.cpp     # Unix socket impl
│   ├── runtime/
│   │   ├── sandbox.hpp           # Process isolation
│   │   ├── sandbox.cpp           # Namespaces + cgroups
│   │   ├── agent_process.hpp     # Agent lifecycle
│   │   └── agent_process.cpp     # Spawn/stop/manage
│   └── util/
│       ├── logger.hpp
│       └── logger.cpp
├── agents/
│   ├── python_sdk/
│   │   ├── pyproject.toml       # Package configuration
│   │   └── clove_sdk/           # Python SDK package
│   │       ├── client.py         # Main client
│   │       ├── agentic.py        # Agentic loop framework
│   │       ├── remote.py         # Remote agent client
│   │       └── fleet.py          # Fleet management client
│   ├── dashboard/                # Web monitoring dashboard
│   │   ├── index.html            # Single-page dashboard app
│   │   ├── ws_proxy.py           # WebSocket proxy bridge
│   │   └── README.md             # Dashboard documentation
│   ├── llm_service/
│   │   ├── llm_service.py        # LLM subprocess (google-genai)
│   │   └── requirements.txt      # Python dependencies
│   ├── mcp/                      # MCP Server for Claude Desktop
│   │   ├── mcp_server.py         # MCP protocol server
│   │   └── README.md             # Installation instructions
│   ├── adapters/                 # Framework Adapters
│   │   ├── langchain_adapter.py  # LangChain integration
│   │   ├── crewai_adapter.py     # CrewAI integration
│   │   └── autogen_adapter.py    # AutoGen integration
│   └── examples/
│       ├── hello_agent.py        # Echo test
│       ├── thinking_agent.py     # LLM interaction
│       ├── echo_test.py          # [NEW] Deployment test agent
│       ├── health_check.py       # [NEW] Health check agent
│       └── ...                   # Other demo agents
├── cli/                          # [NEW] Clove CLI Tool
│   ├── clove.py                # Main CLI entry point
│   ├── config.py                 # Config management (~/.clove/)
│   ├── relay_api.py              # REST API client
│   ├── setup.py                  # CLI installation script
│   ├── requirements.txt          # CLI dependencies
│   └── commands/
│       ├── deploy.py             # deploy docker|aws|gcp
│       ├── status.py             # fleet status
│       ├── machines.py           # machines list|remove|ssh|logs
│       ├── agent.py              # agent run|list|stop|create
│       └── tokens.py             # tokens create|list|revoke
├── relay/                        # Relay Server
│   ├── relay_server.py           # WebSocket relay + REST API
│   ├── api.py                    # [NEW] REST API endpoints
│   ├── fleet.py                  # [NEW] Fleet management
│   ├── tokens.py                 # [NEW] Token persistence
│   ├── auth.py                   # Authentication
│   ├── router.py                 # Message routing
│   └── requirements.txt          # Server dependencies
├── deploy/                       # [NEW] Deployment Assets
│   ├── docker/
│   │   ├── Dockerfile            # Clove kernel container
│   │   ├── docker-compose.yml    # Full stack deployment
│   │   ├── entrypoint.sh         # Container startup
│   │   └── .dockerignore
│   ├── terraform/
│   │   ├── aws/                  # AWS EC2 module
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── cloud-init.yaml
│   │   └── gcp/                  # GCP Compute module
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       ├── outputs.tf
│   │       └── cloud-init.yaml
│   └── systemd/
│       ├── clove-kernel.service
│       ├── clove-tunnel.service
│       └── clove-relay.service
├── build/
│   └── clove_kernel
├── CMakeLists.txt
├── vcpkg.json
├── .env.example
├── STATUS.md
└── README.md
```

---

## Overall Progress

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Development Environment | **COMPLETE** |
| Phase 1 | Echo Server (IPC) | **COMPLETE** |
| Phase 2 | Sandboxing | **COMPLETE** |
| Phase 3 | LLM Integration (Gemini) | **COMPLETE** |
| Phase 4 | OS-Level Demonstrations | **COMPLETE** |
| Phase 5 | Universal Agent Runtime | **COMPLETE** |
| Phase 6 | Remote Connectivity | **COMPLETE** |
| Phase 7 | Relay Server | **COMPLETE** |
| Phase 8 | Cloud Deployment System | **COMPLETE** |
| — | Metrics System | **COMPLETE** |
| Phase 9 | World Simulation | **NEXT** |
| Phase 10 | Agent Gymnasium | **FUTURE** |
| Phase 11 | Benchmark Framework | **FUTURE** |

---

## New Syscalls (Phase 2)

| Opcode | Name | Description |
|--------|------|-------------|
| 0x10 | SYS_SPAWN | Spawn a sandboxed agent |
| 0x11 | SYS_KILL | Kill a running agent |
| 0x12 | SYS_LIST | List all agents |

### SYS_SPAWN Payload (JSON)
```json
{
  "name": "agent1",
  "script": "/path/to/script.py",
  "sandboxed": true,
  "network": false,
  "limits": {
    "memory": 268435456,
    "max_pids": 64,
    "cpu_quota": 100000
  }
}
```

### SYS_SPAWN Response
```json
{
  "id": 2,
  "name": "agent1",
  "pid": 12345,
  "status": "running"
}
```

---

## How to Run

### Start the Kernel
```bash
cd /home/anixd/Documents/CLOVE/build
./clove_kernel
```

### Run with Full Isolation (requires root)
```bash
sudo ./clove_kernel
```

### Spawn Test
```bash
python3 /home/anixd/Documents/CLOVE/agents/examples/spawn_test.py
```

### Python SDK Usage
```python
from clove_sdk import CloveClient

with CloveClient() as client:
    # Spawn an agent
    result = client.spawn(
        name="worker1",
        script="/path/to/worker.py",
        sandboxed=True
    )
    print(f"Spawned: {result}")

    # List agents
    agents = client.list_agents()
    print(f"Running: {agents}")

    # Kill agent
    client.kill(name="worker1")
```

---

## Sandbox Features

### Implemented
- Linux namespaces (PID, NET, MNT, UTS)
- cgroups v2 resource limits (memory, CPU, PIDs)
- Agent process lifecycle management
- Graceful shutdown with SIGTERM/SIGKILL
- Fallback to fork() when not root

### Limitations
- Full isolation requires root/CAP_SYS_ADMIN
- cgroups require mounted cgroup v2 filesystem
- Without root, agents run without namespace isolation

---

## Commands Reference

```bash
# Build
cd /home/anixd/Documents/CLOVE/build
make -j$(nproc)

# Run kernel (normal)
./clove_kernel

# Run kernel (with full sandbox isolation)
sudo ./clove_kernel

# Run tests
python3 /home/anixd/Documents/CLOVE/agents/examples/hello_agent.py
python3 /home/anixd/Documents/CLOVE/agents/examples/spawn_test.py
```

---

## SYS_THINK Syscall (Phase 3 - Updated)

| Opcode | Name | Description |
|--------|------|-------------|
| 0x01 | SYS_THINK | Send prompt to Gemini LLM (multimodal) |

### SYS_THINK Request (JSON)

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

All fields except `prompt` are optional. For backward compatibility, plain text strings are also accepted.

### SYS_THINK Response (JSON)

```json
{
  "success": true,
  "content": "LLM response text",
  "tokens": 123,
  "error": null
}
```

If error:
```json
{
  "success": false,
  "content": "",
  "error": "Error message"
}
```

---

## LLM Configuration

### Option 1: .env File (Recommended)

```bash
# Copy template and edit
cp .env.example .env

# Add your API key
echo "GEMINI_API_KEY=your-api-key" >> .env
```

The .env file is automatically loaded from:
1. Current working directory
2. Project root (relative to executable)
3. Parent directories

### Option 2: Environment Variable

```bash
export GEMINI_API_KEY="your-api-key"
# Or
export GOOGLE_API_KEY="your-api-key"
```

### Python Dependency

The LLM service requires the google-genai package:
```bash
pip3 install google-genai
```

### Configurable Options

| Variable | Description | Default |
|----------|-------------|---------|
| GEMINI_API_KEY | Google Gemini API key | (none) |
| GOOGLE_API_KEY | Fallback API key | (none) |
| GEMINI_MODEL | Model name | gemini-2.0-flash |

---

## How to Test LLM

```bash
# Start kernel with API key
export GEMINI_API_KEY="your-key"
cd /home/anixd/Documents/CLOVE/build
./clove_kernel

# In another terminal
python3 /home/anixd/Documents/CLOVE/agents/examples/thinking_agent.py
```

---

## Next Steps (Phase 4: Priority Order)

**Primary Focus:** OS-Level Demonstrations (prove why Clove must exist)

1. **4.1 Crash-Resistant Agents** - Fault isolation demo (highest impact) **DONE**
2. **4.3 Untrusted Execution** - Security story ("Docker-lite for AI")
3. **4.2 LLM Contention** - Fair scheduling ("kernel scheduler for LLM access")
4. **4.4 Supervisor Agent** - PID 1 semantics ("systemd for AI agents")
5. **4.5 Agent Pipelines** - Real IPC benchmarks ("processes, not coroutines")

---

## Phase 5: Universal Agent Runtime (Host Access)

**Vision:** Clove becomes the universal runtime layer that ANY agent/workflow can plug into - with controlled access to your PC.

```
┌─────────────────────────────────────────────────────────────┐
│              AGENT FRAMEWORKS (plug into Clove)           │
│  LangChain │ CrewAI │ AutoGen │ n8n │ Custom │ MCP Clients  │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │     Clove Kernel      │
              │   (Permissions + Audit) │
              └────────────┬────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Your Files         Your Apps          Your APIs
```

### 5.1 Permission System **COMPLETE**

Implemented a comprehensive permission system in the kernel:

**Permission Levels:**
| Level | Description |
|-------|-------------|
| UNRESTRICTED | No restrictions (full access) |
| STANDARD | Default restrictions for safe operation |
| SANDBOXED | Strict restrictions, limited paths |
| READONLY | Can only read, no writes or execution |
| MINIMAL | Almost no permissions |

**Permission Features:**
- Path validation using glob patterns (fnmatch)
- Command filtering with blocked command list
- Domain whitelist for HTTP requests
- LLM quota enforcement (tokens and calls)
- Default blocked paths (credentials, secrets, SSH keys)
- Default blocked commands (rm -rf, sudo, fork bombs)

| Task | Status | Notes |
|------|--------|-------|
| Design permission schema | [x] Done | JSON format in permissions.hpp |
| Implement permission validation in kernel | [x] Done | permissions.cpp |
| Add path validation to SYS_READ/SYS_WRITE | [x] Done | fnmatch glob patterns |
| Add command filtering to SYS_EXEC | [x] Done | Blocked commands list |
| Implement SYS_HTTP with domain whitelist | [x] Done | Domain extraction + matching |
| Add LLM quota enforcement | [x] Done | Token + call limits |
| New syscalls: SYS_GET_PERMS, SYS_SET_PERMS | [x] Done | Opcodes 0x40, 0x41 |

### 5.2 Host Access Syscalls **COMPLETE**

| Syscall | Opcode | Description | Permission Model |
|---------|--------|-------------|------------------|
| SYS_READ | 0x02 | Read file from host | Path whitelist |
| SYS_WRITE | 0x03 | Write file to host | Path whitelist |
| SYS_EXEC | 0x04 | Run shell command | Command filtering |
| SYS_HTTP | 0x50 | Make HTTP request | Domain whitelist |
| SYS_GET_PERMS | 0x40 | Get agent permissions | Always allowed |
| SYS_SET_PERMS | 0x41 | Set agent permissions | Requires elevation |

| Task | Status | Notes |
|------|--------|-------|
| Implement SYS_READ with path validation | [x] Done | Whitelist paths |
| Implement SYS_WRITE with path validation | [x] Done | Whitelist paths |
| Implement SYS_EXEC with approval | [x] Done | Command filtering |
| Implement SYS_HTTP with domain whitelist | [x] Done | Uses curl subprocess |
| Update Python SDK | [x] Done | New methods added |

### 5.3 Framework Adapters **COMPLETE**

| Adapter | Status | Notes |
|---------|--------|-------|
| langchain_adapter.py | [x] Done | LangChain tools → Clove syscalls |
| crewai_adapter.py | [x] Done | CrewAI agents → Clove processes |
| autogen_adapter.py | [x] Done | AutoGen → Clove |

**LangChain Adapter:**
- `CloveToolkit` - Collection of all tools
- Individual tools: `CloveReadTool`, `CloveWriteTool`, `CloveExecTool`, etc.
- Works with any LangChain agent (ReAct, etc.)

**CrewAI Adapter:**
- `CloveCrewTools` - Tools for CrewAI agents
- `CloveCrewAgent` - Factory for creating agents
- Pre-built agent types: researcher, developer, orchestrator

**AutoGen Adapter:**
- `CloveAssistant` - AssistantAgent with Clove tools
- `CloveUserProxy` - UserProxy that executes through Clove
- Code execution routed through Clove permission system

### 5.4 MCP Integration (Claude Desktop) **COMPLETE**

Clove is now an MCP server so Claude Desktop can:
- Spawn agents on your PC
- Access files (with permission)
- Run commands (with approval)
- Make HTTP requests
- All through the safe Clove layer

| Task | Status | Notes |
|------|--------|-------|
| Implement MCP server protocol | [x] Done | JSON-RPC 2.0 over stdio |
| Expose Clove syscalls as MCP tools | [x] Done | 8 tools exposed |
| Add to Claude Desktop config | [x] Done | README with instructions |

**MCP Tools Exposed:**
| Tool | Description |
|------|-------------|
| clove_read | Read files |
| clove_write | Write files |
| clove_exec | Execute commands |
| clove_think | Query LLM |
| clove_spawn | Spawn agents |
| clove_list_agents | List running agents |
| clove_kill | Kill agents |
| clove_http | HTTP requests |

---

## Phase 5 Summary

**What this enables:**
- Any agent framework runs ON Clove (safely)
- Claude Desktop gets controlled PC access
- Workflows from n8n/etc run in isolation
- Universal "write once, run anywhere" for agents

**Positioning:**
- Phase 4: "Prove why Clove must exist" (demos)
- Phase 5: "Make Clove the universal agent runtime" (integration)

---

**Secondary (After Phase 5):**
- Streaming responses (SSE)
- Conversation history/context
- Tool use / function calling
- Persistent agent state
- Multi-LLM support (OpenAI, Claude, local models)

---

## Project Positioning

Two compelling narratives for Clove:

1. **"systemd for AI agents"** - OS-style supervision, lifecycle, restart policies
2. **"microkernel for autonomous compute"** - Isolation, scheduling, resource control

---

## Notes

- All tests passing as of 2026-01-22
- Sandbox fallback works correctly without root
- Python SDK fully updated with spawn/kill/list/think (multimodal support)
- **LLM client uses Python subprocess (google-genai SDK)** instead of C++ HTTP
- Automatic .env file loading in both C++ and Python
- Multimodal support: text + images
- Extended think() options: system_instruction, thinking_level, temperature
- **Phase 5 complete:** Permission system, host access syscalls, MCP server, and framework adapters all working
- **Web Dashboard:** Real-time browser-based monitoring with WebSocket proxy
- **Agentic Loop:** Claude Code-style autonomous agent framework for iterative task execution
- **Phase 6-7 complete:** Remote connectivity via relay server, tunnel client
- **Phase 8 complete:** Cloud Deployment System with CLI tool, Docker/AWS/GCP support, fleet management
- **Metrics System complete:** Kernel-level metrics collection (CPU, memory, disk, network, process, cgroup)
- **Next focus:** World Simulation (Phase 9) - virtual environments for safe agent testing

---

## Phase 8: Cloud Deployment System **COMPLETE**

### CLI Commands Implemented

| Command | Description |
|---------|-------------|
| `clove deploy docker [--name NAME]` | Deploy kernel to Docker |
| `clove deploy aws [--region] [--instance-type]` | Deploy to AWS EC2 |
| `clove deploy gcp [--zone] [--machine-type]` | Deploy to GCP Compute |
| `clove status` | Show fleet status |
| `clove machines list` | List all machines |
| `clove machines show <id>` | Show machine details |
| `clove machines remove <id>` | Remove machine |
| `clove machines ssh <id>` | SSH into machine |
| `clove machines logs <id>` | View machine logs |
| `clove agent run <script> --machine <id>` | Run agent on machine |
| `clove agent list` | List running agents |
| `clove agent stop <id> --machine <id>` | Stop agent |
| `clove agent create <name> [--template]` | Create agent from template |
| `clove tokens create machine` | Create machine token |
| `clove tokens create agent` | Create agent token |
| `clove tokens list` | List tokens |
| `clove tokens revoke <id>` | Revoke token |
| `clove config` | Show configuration |
| `clove config-set <key> <value>` | Set configuration |

### Relay Server REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/status` | GET | Server status |
| `/api/v1/health` | GET | Health check |
| `/api/v1/machines` | GET | List machines |
| `/api/v1/machines/{id}` | GET | Get machine |
| `/api/v1/machines` | POST | Register machine |
| `/api/v1/machines/{id}` | DELETE | Remove machine |
| `/api/v1/agents` | GET | List agents |
| `/api/v1/agents/deploy` | POST | Deploy agent |
| `/api/v1/agents/{id}/stop` | POST | Stop agent |
| `/api/v1/tokens` | GET | List tokens |
| `/api/v1/tokens/machine` | POST | Create machine token |
| `/api/v1/tokens/agent` | POST | Create agent token |
| `/api/v1/tokens/{id}` | DELETE | Revoke token |

### Quick Start

```bash
# Install CLI
pip install -e cli/

# Deploy locally with Docker
clove deploy docker --name my-kernel

# Check status
clove status

# Run an agent
clove agent run agents/examples/echo_test.py --machine docker-my-kernel-xxx

# Or deploy to cloud
clove deploy aws --region us-east-1 --instance-type t3.small
```

---

## Future Directions

### Phase 6: World Simulation **NEXT**

**Goal:** Create isolated, configurable environments ("worlds") where agents can operate without affecting real systems.

**Capabilities:**
- **Filesystem virtualization** - Mount custom directory trees, inject files, track modifications
- **Network mocking** - Mock APIs, inject latency/failures, restrict connectivity
- **Time manipulation** - Accelerate time for long-running tests, schedule events
- **Event injection** - Trigger failures, load spikes, data corruption
- **State snapshots** - Save/restore world state for reproducible testing

**New Syscalls:**
| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_WORLD_CREATE` | `0xA0` | Create a new world from config |
| `SYS_WORLD_DESTROY` | `0xA1` | Destroy a world and cleanup |
| `SYS_WORLD_LIST` | `0xA2` | List active worlds |
| `SYS_WORLD_JOIN` | `0xA3` | Join an agent to a world |
| `SYS_WORLD_LEAVE` | `0xA4` | Remove agent from world |
| `SYS_WORLD_EVENT` | `0xA5` | Inject event into world |
| `SYS_WORLD_STATE` | `0xA6` | Get world state/metrics |
| `SYS_WORLD_SNAPSHOT` | `0xA7` | Save world state |
| `SYS_WORLD_RESTORE` | `0xA8` | Restore from snapshot |

### Phase 7: Remote Connectivity

**Goal:** Cloud agents can connect to your local kernel securely via relay server.

**Architecture:** Kernel connects outbound to relay server (works behind NAT). Cloud agents also connect to relay. Same syscall protocol works over WebSocket.

### Phase 8: Agent Gymnasium

**Vision:** Library of pre-built worlds for training and evaluating autonomous agents.

**Use cases:**
- Test SRE agents against simulated outages
- Evaluate coding agents in realistic project environments
- Benchmark multi-agent collaboration in shared worlds
- Train agents on edge cases without risking production systems

### Phase 9: Benchmark Framework

**Goal:** Standardized task suites, metrics collection, and comparison tools for agent evaluation.

**Why Clove for benchmarks:**
- **Identical conditions** - Same resource limits, same sandboxing for all agents
- **No interference** - Agents can't affect each other's performance
- **Reproducible** - Controlled environment ensures consistent results
- **Real metrics** - Kernel-level resource tracking (not just token counts)
- **Failure handling** - Measure how agents recover from crashes/timeouts

---

## Roadmap Summary

| Phase | Feature | Status | Priority |
|-------|---------|--------|----------|
| **Done** | Core Kernel | **Complete** | - |
| **Done** | IPC, State, Permissions | **Complete** | - |
| **Done** | Events, Network, Tunnel | **Complete** | - |
| **Done** | World Engine | **Complete** | - |
| **Done** | CLI, Relay, Metrics | **Complete** | - |
| **Done** | Hot Reload | **Complete** | - |
| **Done** | Benchmark Suite | **Complete** | - |
| **Next** | PAUSE/RESUME Syscalls | Not Started | High |
| **Next** | AUDIT Logging | Not Started | High |
| **Next** | REPLAY Mechanism | Not Started | Medium |
| Later | Multi-Agent Orchestration | Not Started | Medium |
| Later | Resource Quotas | Not Started | Medium |
| Later | Multi-Node Cluster | Not Started | Medium |
| Later | clove.yaml / clove up | Not Started | Medium |
| Future | Clove Cloud (managed) | Not Started | Low |

---

## Success Metrics

| Metric | Target | Timeframe |
|--------|--------|-----------|
| GitHub stars | 1,000 | 3 months |
| Discord members | 500 | 3 months |
| Production users | 10 | 6 months |
| Agents running on Clove | 10,000 | 6 months |
