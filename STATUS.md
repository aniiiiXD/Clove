# AgentOS Development Status

**Last Updated:** 2026-01-17

---

## Current Phase: Phase 4 - OS-Level Demonstrations **IN PROGRESS**

**Goal:** Prove why AgentOS must exist with workflows that *only* an OS-level kernel can handle cleanly.

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

## Phase 4: OS-Level Workflows (Why AgentOS Exists)

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
- Spawn 10 agents
- All request LLM simultaneously
- Kernel queues, rate-limits, multiplexes responses

**Target output:**
```
Agent   Tokens   Latency   Throttled
A       1200     1.2s      no
B       500      0.8s      yes
C       800      1.5s      yes
...
```

**Positioning:** *"AgentOS is a kernel scheduler for LLM access"*

| Task | Status | Notes |
|------|--------|-------|
| Implement LLM request queue in kernel | [ ] Pending | Fair scheduling |
| Add rate limiting per agent | [ ] Pending | Token/request limits |
| Create llm_contention_demo.py | [ ] Pending | 10 concurrent agents |
| Add metrics (latency, tokens, throttled) | [ ] Pending | |
| Document behavior | [ ] Pending | |

---

### 4.3 Untrusted Agent Execution (Security Story)

**What to demonstrate:**
- Run a third-party agent
- Agent attempts: filesystem access, network access, fork bomb
- Kernel denies/kills

**Target output:**
```
DENIED: filesystem access
DENIED: network access
KILLED: PID limit exceeded
```

**Positioning:** *"AgentOS is Docker-lite for AI agents"*

| Task | Status | Notes |
|------|--------|-------|
| Create malicious_fs_agent.py | [ ] Pending | Attempts file reads |
| Create malicious_net_agent.py | [ ] Pending | Attempts network |
| Create fork_bomb_agent.py | [ ] Pending | Attempts fork bomb |
| Create security_demo.py | [ ] Pending | Run and observe |
| Verify sandbox blocks all attempts | [ ] Pending | Needs root |
| Document behavior | [ ] Pending | |

---

### 4.4 Supervisor / Init-Style Agent (PID 1 Semantics)

**What to demonstrate:**
- Supervisor agent watches child agents
- Restarts failed agents
- Escalates unrecoverable failures

**Mirrors:** `systemd`, Kubernetes controllers

| Task | Status | Notes |
|------|--------|-------|
| Create supervisor_agent.py | [ ] Pending | PID 1 semantics |
| Implement child watching | [ ] Pending | Monitor spawned agents |
| Implement restart policy | [ ] Pending | Auto-restart on crash |
| Implement escalation | [ ] Pending | Alert on repeated failures |
| Create supervisor_demo.py | [ ] Pending | Full demo |
| Document behavior | [ ] Pending | |

---

### 4.5 Agent Pipelines with Real IPC

**What to demonstrate:**
- Agent A → parses input
- Agent B → runs LLM reasoning
- Agent C → verifies output
- Real kernel-mediated IPC (not Python function calls)

**Positioning:** *"Agents are processes, not coroutines."*

| Task | Status | Notes |
|------|--------|-------|
| Create parser_agent.py | [ ] Pending | Stage 1: parse |
| Create reasoner_agent.py | [ ] Pending | Stage 2: LLM |
| Create verifier_agent.py | [ ] Pending | Stage 3: verify |
| Implement inter-agent messaging | [ ] Pending | Kernel-mediated |
| Create pipeline_demo.py | [ ] Pending | Orchestrator |
| Benchmark IPC performance | [ ] Pending | Latency, throughput |
| Document behavior | [ ] Pending | |

---

## Phase 4 Progress

| # | Workflow | Status | Notes |
|---|----------|--------|-------|
| 4.1 | Crash-Resistant Agents | [x] **COMPLETE** | Fault isolation demo working |
| 4.2 | LLM Contention | [ ] Pending | Fair scheduling |
| 4.3 | Untrusted Execution | [ ] Pending | Security story |
| 4.4 | Supervisor Agent | [ ] Pending | PID 1 semantics |
| 4.5 | Agent Pipelines | [ ] Pending | Real IPC |

---

## Existing Examples (Reframed)

**SDK Onboarding / Smoke Tests:**
- `hello_agent.py` - Basic IPC verification
- `thinking_agent.py` - LLM connectivity test
- `spawn_test.py` - Lifecycle basics
- `worker_agent.py` - Spawnable agent template

**OS-Level Demonstrations (Phase 4):**
- `fault_isolation_demo.py` - **NEW** - Spawns 3 agents, proves isolation
- `cpu_hog_agent.py` - **NEW** - CPU stress test (throttled by cgroups)
- `memory_hog_agent.py` - **NEW** - Memory leak (killed by cgroups)
- `healthy_agent.py` - **NEW** - Well-behaved agent (survives failures)

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
│                    AgentOS Kernel (C++)                      │
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
| 1.6 | Write Python SDK | [x] Done | agents/python_sdk/agentos.py |
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
AGENTOS/
├── src/
│   ├── main.cpp                  # Entry point
│   ├── kernel/
│   │   ├── kernel.hpp            # Kernel class + LLM config
│   │   ├── kernel.cpp            # + spawn/kill/list/think handlers
│   │   ├── reactor.hpp           # Event loop
│   │   ├── reactor.cpp           # epoll implementation
│   │   ├── llm_client.hpp        # LLM subprocess manager
│   │   └── llm_client.cpp        # Subprocess IPC, .env loading
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
│   │   └── agentos.py            # Client SDK (multimodal think())
│   ├── llm_service/
│   │   ├── llm_service.py        # LLM subprocess (google-genai)
│   │   └── requirements.txt      # Python dependencies
│   └── examples/
│       ├── hello_agent.py        # Echo test
│       ├── thinking_agent.py     # LLM interaction
│       ├── worker_agent.py       # Spawnable worker
│       ├── spawn_test.py         # Spawn test script
│       ├── fault_isolation_demo.py  # OS-level fault isolation
│       ├── cpu_hog_agent.py      # CPU stress test
│       ├── memory_hog_agent.py   # Memory stress test
│       └── healthy_agent.py      # Well-behaved agent
├── build/
│   └── agentos_kernel
├── CMakeLists.txt
├── vcpkg.json
├── .env.example                  # Environment template
├── .env                          # Local config (not in git)
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
| Phase 4 | OS-Level Demonstrations | **IN PROGRESS** |
| Phase 5 | Universal Agent Runtime | **PLANNED** |

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
cd /home/anixd/Documents/AGENTOS/build
./agentos_kernel
```

### Run with Full Isolation (requires root)
```bash
sudo ./agentos_kernel
```

### Spawn Test
```bash
python3 /home/anixd/Documents/AGENTOS/agents/examples/spawn_test.py
```

### Python SDK Usage
```python
from agentos import AgentOSClient

with AgentOSClient() as client:
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
cd /home/anixd/Documents/AGENTOS/build
make -j$(nproc)

# Run kernel (normal)
./agentos_kernel

# Run kernel (with full sandbox isolation)
sudo ./agentos_kernel

# Run tests
python3 /home/anixd/Documents/AGENTOS/agents/examples/hello_agent.py
python3 /home/anixd/Documents/AGENTOS/agents/examples/spawn_test.py
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
cd /home/anixd/Documents/AGENTOS/build
./agentos_kernel

# In another terminal
python3 /home/anixd/Documents/AGENTOS/agents/examples/thinking_agent.py
```

---

## Next Steps (Phase 4: Priority Order)

**Primary Focus:** OS-Level Demonstrations (prove why AgentOS must exist)

1. **4.1 Crash-Resistant Agents** - Fault isolation demo (highest impact) **DONE**
2. **4.3 Untrusted Execution** - Security story ("Docker-lite for AI")
3. **4.2 LLM Contention** - Fair scheduling ("kernel scheduler for LLM access")
4. **4.4 Supervisor Agent** - PID 1 semantics ("systemd for AI agents")
5. **4.5 Agent Pipelines** - Real IPC benchmarks ("processes, not coroutines")

---

## Phase 5: Universal Agent Runtime (Host Access)

**Vision:** AgentOS becomes the universal runtime layer that ANY agent/workflow can plug into - with controlled access to your PC.

```
┌─────────────────────────────────────────────────────────────┐
│              AGENT FRAMEWORKS (plug into AgentOS)           │
│  LangChain │ CrewAI │ AutoGen │ n8n │ Custom │ MCP Clients  │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │     AgentOS Kernel      │
              │   (Permissions + Audit) │
              └────────────┬────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Your Files         Your Apps          Your APIs
```

### 5.1 Host Access Syscalls

| Syscall | Description | Permission Model |
|---------|-------------|------------------|
| SYS_READ | Read file from host | Path whitelist |
| SYS_WRITE | Write file to host | Path whitelist |
| SYS_EXEC | Run shell command | Command approval |
| SYS_HTTP | Make HTTP request | Domain whitelist |
| SYS_NOTIFY | Desktop notification | Always allowed |
| SYS_CLIPBOARD | Read/write clipboard | User approval |

| Task | Status | Notes |
|------|--------|-------|
| Implement SYS_READ with path validation | [ ] Pending | Whitelist paths |
| Implement SYS_WRITE with path validation | [ ] Pending | Whitelist paths |
| Implement SYS_EXEC with approval | [ ] Pending | Command filtering |
| Implement SYS_HTTP with domain whitelist | [ ] Pending | Network control |
| Add permission model to spawn config | [ ] Pending | Capability system |
| Add audit logging for all host access | [ ] Pending | Security trail |

### 5.2 Permission Model

```python
# Agents declare what they need access to
client.spawn(
    name="file-organizer",
    script="organizer.py",
    permissions={
        "filesystem": {
            "read": ["/home/user/Documents/*"],
            "write": ["/home/user/Documents/organized/*"]
        },
        "exec": ["git", "python"],
        "network": ["api.github.com"],
        "llm": {"budget": 10000}  # max tokens
    }
)
```

| Task | Status | Notes |
|------|--------|-------|
| Design permission schema | [ ] Pending | JSON format |
| Implement permission validation in kernel | [ ] Pending | Check on each syscall |
| Add permission inheritance for child agents | [ ] Pending | Can't exceed parent |
| User approval flow for sensitive ops | [ ] Pending | Interactive prompts |

### 5.3 Framework Adapters

| Adapter | Status | Notes |
|---------|--------|-------|
| langchain_adapter.py | [ ] Pending | LangChain tools → AgentOS syscalls |
| crewai_adapter.py | [ ] Pending | CrewAI agents → AgentOS processes |
| autogen_adapter.py | [ ] Pending | AutoGen → AgentOS |
| mcp_server.py | [ ] Pending | AgentOS as MCP server for Claude Desktop |

### 5.4 MCP Integration (Claude Desktop)

Make AgentOS an MCP server so Claude Desktop can:
- Spawn agents on your PC
- Access files (with permission)
- Run commands (with approval)
- All through the safe AgentOS layer

| Task | Status | Notes |
|------|--------|-------|
| Implement MCP server protocol | [ ] Pending | JSON-RPC over stdio |
| Expose AgentOS syscalls as MCP tools | [ ] Pending | read, write, exec, think |
| Add to Claude Desktop config | [ ] Pending | Installation docs |

---

## Phase 5 Summary

**What this enables:**
- Any agent framework runs ON AgentOS (safely)
- Claude Desktop gets controlled PC access
- Workflows from n8n/etc run in isolation
- Universal "write once, run anywhere" for agents

**Positioning:**
- Phase 4: "Prove why AgentOS must exist" (demos)
- Phase 5: "Make AgentOS the universal agent runtime" (integration)

---

**Secondary (After Phase 5):**
- Streaming responses (SSE)
- Conversation history/context
- Tool use / function calling
- Persistent agent state
- Multi-LLM support (OpenAI, Claude, local models)

---

## Project Positioning

Two compelling narratives for AgentOS:

1. **"systemd for AI agents"** - OS-style supervision, lifecycle, restart policies
2. **"microkernel for autonomous compute"** - Isolation, scheduling, resource control

---

## Notes

- All tests passing as of 2026-01-17
- Sandbox fallback works correctly without root
- Python SDK fully updated with spawn/kill/list/think (multimodal support)
- **LLM client uses Python subprocess (google-genai SDK)** instead of C++ HTTP
- Automatic .env file loading in both C++ and Python
- Multimodal support: text + images
- Extended think() options: system_instruction, thinking_level, temperature
- **Current examples are SDK onboarding / smoke tests** - not the flagship demos
- **Phase 4 goal: adversarial examples that only AgentOS can handle cleanly**
