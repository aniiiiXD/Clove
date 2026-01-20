# AgentOS Kernel Extensions Plan

## Overview

Extend the AgentOS kernel to support distributed agents, inter-agent communication, shared state, permissions, and cloud connectivity - enabling agents running anywhere to securely interact with your local system.

---

## Architecture Vision

```
┌──────────────────────────── CLOUD ────────────────────────────┐
│                                                                │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│   │ Agent A  │    │ Agent B  │    │ Agent C  │               │
│   │ (Worker) │    │ (Coder)  │    │(Researcher)              │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘               │
│        │               │               │                      │
│        └───────────────┼───────────────┘                      │
│                        │                                      │
│                  ┌─────▼─────┐                                │
│                  │   Relay   │  (AgentOS Cloud Relay)        │
│                  │  Server   │                                │
│                  └─────┬─────┘                                │
│                        │                                      │
└────────────────────────┼──────────────────────────────────────┘
                         │ Secure WebSocket Tunnel
                         │ (Kernel connects OUT)
┌────────────────────────┼──────────────────────────────────────┐
│                        │                                      │
│    YOUR LOCAL SYSTEM   │                                      │
│                        │                                      │
│                  ┌─────▼─────┐                                │
│                  │           │                                │
│                  │  KERNEL   │◄──── Local Agents (Unix sock)  │
│                  │           │                                │
│                  └─────┬─────┘                                │
│                        │                                      │
│        ┌───────────────┼───────────────┐                      │
│        │               │               │                      │
│        ▼               ▼               ▼                      │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│   │  Files  │    │Terminal │    │ Network │                  │
│   │  System │    │  Shell  │    │  Access │                  │
│   └─────────┘    └─────────┘    └─────────┘                  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Inter-Agent Communication (IPC) ✅ COMPLETE

**Goal:** Enable agents to communicate with each other through the kernel.

**Status:** Implemented in kernel. See `SYS_SEND` (0x20), `SYS_RECV` (0x21), `SYS_BROADCAST` (0x22), `SYS_SUBSCRIBE` (0x23) in protocol.hpp.

### New Syscalls

| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_SEND` | `0x20` | Send message to another agent |
| `SYS_RECV` | `0x21` | Receive pending messages |
| `SYS_BROADCAST` | `0x22` | Send message to all agents |

### Protocol

```cpp
// SYS_SEND payload
{
    "to": 123,           // target agent_id (0 = by name)
    "to_name": "worker", // or target by name
    "message": { ... },  // arbitrary JSON payload
    "reply_to": 456      // optional: for request/response pattern
}

// SYS_RECV response
{
    "messages": [
        {
            "from": 123,
            "from_name": "orchestrator",
            "message": { ... },
            "timestamp": 1234567890
        }
    ]
}
```

### Implementation

**Files to modify:**
- `src/ipc/protocol.hpp` - Add new opcodes
- `src/kernel/kernel.hpp` - Add message queues per agent
- `src/kernel/kernel.cpp` - Implement handlers
- `agents/python_sdk/agentos.py` - Add `send()`, `recv()`, `broadcast()`

**Kernel data structures:**
```cpp
// Per-agent message queue
std::unordered_map<uint32_t, std::queue<Message>> agent_mailboxes_;

// Agent name registry
std::unordered_map<std::string, uint32_t> agent_names_;
```

---

## Phase 2: Shared State Store

**Goal:** Agents can store and retrieve shared state through the kernel.

### New Syscalls

| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_STORE` | `0x30` | Store key-value pair |
| `SYS_FETCH` | `0x31` | Retrieve value by key |
| `SYS_DELETE` | `0x32` | Delete a key |
| `SYS_KEYS` | `0x33` | List keys (with optional prefix) |

### Protocol

```cpp
// SYS_STORE payload
{
    "key": "task:123:result",
    "value": { ... },        // any JSON
    "ttl": 3600,             // optional: seconds until expiry
    "scope": "global"        // "global" | "agent" | "session"
}

// SYS_FETCH payload
{
    "key": "task:123:result"
}

// Response
{
    "success": true,
    "value": { ... },
    "exists": true
}
```

### Scopes

- **global** - All agents can access
- **agent** - Only the storing agent can access (namespaced by agent_id)
- **session** - Persists until kernel restart

### Implementation

**Files to modify:**
- `src/ipc/protocol.hpp` - Add opcodes
- `src/kernel/kernel.hpp` - Add state store
- `src/kernel/kernel.cpp` - Implement handlers
- `agents/python_sdk/agentos.py` - Add `store()`, `fetch()`, `delete_key()`, `list_keys()`

**Kernel data structures:**
```cpp
struct StoredValue {
    nlohmann::json value;
    std::chrono::steady_clock::time_point expires_at;
    uint32_t owner_agent_id;
    std::string scope;
};

std::unordered_map<std::string, StoredValue> state_store_;
```

---

## Phase 3: Permission System ✅ COMPLETE

**Goal:** Kernel enforces what each agent is allowed to do.

**Status:** Fully implemented in `src/kernel/permissions.hpp/cpp`. Includes path validation, command filtering, domain whitelist, LLM quotas.

### Permission Model

```cpp
struct AgentPermissions {
    // Syscall permissions
    bool can_exec = true;
    bool can_read = true;
    bool can_write = true;
    bool can_think = true;
    bool can_spawn = false;      // dangerous: spawning other agents
    bool can_network = false;    // HTTP requests

    // Path restrictions
    std::vector<std::string> allowed_read_paths;   // empty = all
    std::vector<std::string> allowed_write_paths;  // empty = all
    std::vector<std::string> blocked_paths;        // always deny

    // Command restrictions
    std::vector<std::string> allowed_commands;     // empty = all
    std::vector<std::string> blocked_commands;     // e.g., "rm -rf", "sudo"

    // Resource limits
    uint64_t max_memory_bytes = 0;     // 0 = unlimited
    uint32_t max_cpu_percent = 0;      // 0 = unlimited
    uint32_t max_llm_calls_per_min = 0;
};
```

### New Syscalls

| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_GET_PERMS` | `0x40` | Get own permissions |
| `SYS_SET_PERMS` | `0x41` | Set agent permissions (privileged) |

### Permission Levels (Presets)

```cpp
enum class PermissionLevel {
    UNRESTRICTED,  // Dev mode - everything allowed
    STANDARD,      // Read/write/exec, no spawn/network
    SANDBOXED,     // Limited paths, no dangerous commands
    READONLY,      // Can only read files, no exec
    MINIMAL        // Can only think (LLM calls)
};
```

### Implementation

**Files to modify:**
- `src/kernel/kernel.hpp` - Add permissions map
- `src/kernel/kernel.cpp` - Check permissions before each syscall
- `agents/python_sdk/agentos.py` - Add `get_permissions()`

---

## Phase 4: Network Syscalls ✅ COMPLETE

**Goal:** Agents can make HTTP requests through the kernel.

**Status:** Implemented `SYS_HTTP` (0x50) with domain whitelist enforcement. Uses curl subprocess.

### New Syscalls

| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_HTTP` | `0x50` | Make HTTP request |
| `SYS_DOWNLOAD` | `0x51` | Download file from URL |

### Protocol

```cpp
// SYS_HTTP payload
{
    "method": "GET",           // GET, POST, PUT, DELETE, etc.
    "url": "https://api.example.com/data",
    "headers": {
        "Authorization": "Bearer xxx"
    },
    "body": "...",             // for POST/PUT
    "timeout": 30
}

// Response
{
    "success": true,
    "status_code": 200,
    "headers": { ... },
    "body": "..."
}
```

### Implementation

**Files to modify:**
- `src/ipc/protocol.hpp` - Add opcodes
- `src/kernel/kernel.cpp` - Implement using cpp-httplib (already a dependency)
- `agents/python_sdk/agentos.py` - Add `http()`, `download()`

---

## Phase 5: Event System (Pub/Sub)

**Goal:** Agents can subscribe to kernel events and receive notifications.

### Event Types

```cpp
enum class EventType {
    AGENT_SPAWNED,      // New agent started
    AGENT_EXITED,       // Agent terminated
    FILE_CHANGED,       // Watched file modified
    MESSAGE_RECEIVED,   // New IPC message
    SYSCALL_BLOCKED,    // Permission denied
    RESOURCE_WARNING,   // Approaching limits
    CUSTOM              // User-defined events
};
```

### New Syscalls

| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_SUBSCRIBE` | `0x60` | Subscribe to event types |
| `SYS_UNSUBSCRIBE` | `0x61` | Unsubscribe from events |
| `SYS_POLL_EVENTS` | `0x62` | Get pending events |
| `SYS_EMIT` | `0x63` | Emit custom event |

### Protocol

```cpp
// SYS_SUBSCRIBE payload
{
    "events": ["AGENT_SPAWNED", "FILE_CHANGED"],
    "filter": {
        "path": "/home/user/project/*"  // for FILE_CHANGED
    }
}

// SYS_POLL_EVENTS response
{
    "events": [
        {
            "type": "AGENT_SPAWNED",
            "data": { "agent_id": 123, "name": "worker" },
            "timestamp": 1234567890
        }
    ]
}
```

### Implementation

**Files to modify:**
- `src/kernel/kernel.hpp` - Add event queues, subscriptions
- `src/kernel/kernel.cpp` - Event emission on actions, poll handler
- `agents/python_sdk/agentos.py` - Add `subscribe()`, `poll_events()`, `emit()`

---

## Phase 6: Remote Connectivity

**Goal:** Cloud agents can connect to your local kernel securely.

### Connection Model: Reverse Tunnel

Kernel connects **outbound** to a relay server. Cloud agents also connect to relay. Relay routes messages.

```
Local Kernel ──WSS──► Relay Server ◄──WSS── Cloud Agent
                          │
                    Routes messages
                    by agent_id/token
```

**Why outbound?**
- No port forwarding needed
- Works behind NAT/firewalls
- Kernel initiates = you control when it's accessible

### Components

1. **Kernel WebSocket Client** - Connects to relay
2. **Relay Server** - Routes messages (can be self-hosted or cloud service)
3. **Cloud Agent SDK** - Connects to relay, same protocol as local

### New Syscalls

| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_TUNNEL_CONNECT` | `0x70` | Connect kernel to relay |
| `SYS_TUNNEL_STATUS` | `0x71` | Check tunnel status |
| `SYS_TUNNEL_DISCONNECT` | `0x72` | Disconnect tunnel |

### Authentication

```cpp
// Kernel connects with machine token
{
    "type": "kernel_auth",
    "machine_id": "my-desktop-abc123",
    "token": "secret-token-here"
}

// Cloud agent connects with agent token
{
    "type": "agent_auth",
    "agent_name": "cloud-worker-1",
    "token": "agent-token-here",
    "target_machine": "my-desktop-abc123"
}
```

### Protocol Over Tunnel

Same syscall protocol, just wrapped in WebSocket frames:

```json
{
    "type": "syscall",
    "agent_id": 123,
    "opcode": "SYS_EXEC",
    "payload": { "command": "ls -la" }
}
```

### Implementation

**New files:**
- `src/kernel/tunnel_client.hpp/cpp` - WebSocket client for relay
- `src/relay/relay_server.cpp` - Relay server (separate binary)
- `agents/python_sdk/remote_client.py` - Cloud agent SDK

**Dependencies:**
- WebSocket library (e.g., boost::beast or websocketpp)
- TLS support for secure connections

---

## Phase 7: Multi-Agent Orchestration

**Goal:** Kernel can coordinate multiple agents working on a task.

### Orchestration Model

```cpp
struct Task {
    uint64_t task_id;
    std::string description;
    std::vector<uint32_t> assigned_agents;
    std::string status;  // "pending", "running", "completed", "failed"
    nlohmann::json result;
};
```

### New Syscalls

| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_TASK_CREATE` | `0x80` | Create orchestrated task |
| `SYS_TASK_ASSIGN` | `0x81` | Assign agent to task |
| `SYS_TASK_STATUS` | `0x82` | Get task status |
| `SYS_TASK_COMPLETE` | `0x83` | Mark task/subtask complete |
| `SYS_TASK_LIST` | `0x84` | List active tasks |

### Workflow Example

```python
# Orchestrator agent
task = client.task_create("Build and test the project")

# Assign workers
client.task_assign(task["id"], agent_id=worker_1, subtask="run tests")
client.task_assign(task["id"], agent_id=worker_2, subtask="check linting")

# Workers complete their subtasks
# (in worker agent)
client.task_complete(task_id, result={"tests_passed": 42})

# Orchestrator polls for completion
status = client.task_status(task["id"])
```

---

## Phase 8: Resource Monitoring & Quotas

**Goal:** Kernel tracks and limits resource usage per agent.

### Metrics Tracked

```cpp
struct AgentMetrics {
    uint64_t memory_bytes;
    uint64_t cpu_time_ms;
    uint32_t syscall_count;
    uint32_t llm_calls;
    uint32_t llm_tokens_used;
    uint64_t bytes_read;
    uint64_t bytes_written;
    uint64_t network_bytes;
};
```

### New Syscalls

| Syscall | Opcode | Description |
|---------|--------|-------------|
| `SYS_METRICS` | `0x90` | Get own metrics |
| `SYS_METRICS_ALL` | `0x91` | Get all agents' metrics (privileged) |
| `SYS_SET_QUOTA` | `0x92` | Set resource quota (privileged) |

### Quota Enforcement

When quota exceeded:
1. Syscall returns error with `QUOTA_EXCEEDED`
2. Event emitted to subscribed agents
3. Optional: agent suspended until quota resets

---

## Implementation Order

| Phase | Priority | Effort | Status |
|-------|----------|--------|--------|
| Phase 1: IPC | High | Medium | ✅ COMPLETE |
| Phase 2: State Store | High | Low | Pending |
| Phase 3: Permissions | Medium | Medium | ✅ COMPLETE |
| Phase 4: Network | Medium | Low | ✅ COMPLETE |
| Phase 5: Events | Medium | Medium | Pending |
| Phase 6: Remote | High | High | Pending |
| Phase 7: Orchestration | Low | Medium | Pending |
| Phase 8: Quotas | Low | Medium | Pending |

**Next priority:** Phase 2 (State Store) or Phase 6 (Remote Connectivity)

---

## File Structure (After All Phases)

```
src/
├── kernel/
│   ├── kernel.cpp/hpp          # Core kernel (extended)
│   ├── permissions.cpp/hpp     # Permission system
│   ├── state_store.cpp/hpp     # Shared state
│   ├── event_bus.cpp/hpp       # Event system
│   ├── tunnel_client.cpp/hpp   # Remote connectivity
│   └── orchestrator.cpp/hpp    # Task orchestration
├── ipc/
│   ├── protocol.hpp            # Extended with new opcodes
│   └── socket_server.cpp/hpp   # Unchanged
└── relay/
    └── relay_server.cpp        # Standalone relay binary

agents/
├── python_sdk/
│   ├── agentos.py              # Extended client
│   ├── agentic.py              # Agentic loop
│   └── remote_client.py        # Cloud agent SDK
└── examples/
    ├── coding_agent.py
    ├── orchestrator_agent.py   # Multi-agent coordination
    └── cloud_worker.py         # Remote agent example
```

---

## Next Steps

**Completed:**
- ✅ Phase 1: IPC (SYS_SEND, SYS_RECV, SYS_BROADCAST, SYS_SUBSCRIBE)
- ✅ Phase 3: Permission System (path validation, command filtering, domain whitelist)
- ✅ Phase 4: Network Syscalls (SYS_HTTP with domain restrictions)

**Up Next:**
1. **Phase 2: State Store** - Shared key-value storage for agent coordination
2. **Phase 6: Remote Connectivity** - Cloud agents connecting to local kernel via relay
3. **Phase 5: Events** - Pub/sub event system for agent notifications

**Also Implemented (not in original plan):**
- Web Dashboard - Real-time browser monitoring UI
- Agentic Loop Framework - Claude Code-style autonomous agent execution
