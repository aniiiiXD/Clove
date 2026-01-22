# Clove Architecture

## Overview

Clove is a microkernel for AI agents. It provides OS-level isolation, resource control, and fair scheduling for autonomous agents. The system supports both local execution and cloud deployment through a relay server architecture.

## Local Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Clove Kernel (C++23)                        │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Reactor   │  │   LLM Client    │  │   Agent Manager     │  │
│  │   (epoll)   │  │ (subprocess)    │  │   (Sandbox/Fork)    │  │
│  └──────┬──────┘  └────────┬────────┘  └──────────┬──────────┘  │
│         │                  │                       │             │
│         └──────────────────┼───────────────────────┘             │
│                            │                                     │
│              Unix Domain Socket (/tmp/clove.sock)              │
└────────────────────────────┼─────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │ Agent 1 │          │ Agent 2 │          │ Agent 3 │
   │(Python) │          │(Python) │          │(Python) │
   └─────────┘          └─────────┘          └─────────┘
```

## Cloud/Fleet Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         YOUR TERMINAL                             │
│  $ clove deploy aws    $ clove status    $ clove agent run │
└───────────────────────────────┬──────────────────────────────────┘
                                │ REST API
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    RELAY SERVER (Cloud/Self-Hosted)               │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐             │
│   │  REST API  │    │  WebSocket │    │   Fleet    │             │
│   │ (CLI mgmt) │    │    Hub     │    │  Manager   │             │
│   │  :8766     │    │   :8765    │    │            │             │
│   └────────────┘    └────────────┘    └────────────┘             │
│        │                   │                 │                    │
│        └───────────────────┴─────────────────┘                    │
└────────────────────────────┬─────────────────────────────────────┘
                             │ WebSocket
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  AWS EC2        │ │  GCP Compute    │ │  Docker Local   │
│  Clove Kernel │ │  Clove Kernel │ │  Clove Kernel │
│  + Tunnel       │ │  + Tunnel       │ │  + Tunnel       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Components

### Kernel (`src/kernel/`)

| File | Purpose |
|------|---------|
| `kernel.hpp/cpp` | Main kernel class, syscall routing, IPC mailboxes |
| `reactor.hpp/cpp` | epoll-based event loop |
| `llm_client.hpp/cpp` | Spawns Python subprocess for LLM calls |
| `permissions.hpp/cpp` | Permission validation (paths, commands, domains) |
| `metrics/metrics.hpp/cpp` | System and agent metrics collection |

### IPC (`src/ipc/`)

| File | Purpose |
|------|---------|
| `protocol.hpp` | Binary protocol definition, opcodes, message format |
| `socket_server.hpp/cpp` | Unix domain socket server |

**Protocol Format:**
```
┌──────────┬──────────┬────────┬──────────────┬─────────┐
│  Magic   │ Agent ID │ Opcode │ Payload Size │ Payload │
│ (4 bytes)│ (4 bytes)│(1 byte)│  (8 bytes)   │  (var)  │
└──────────┴──────────┴────────┴──────────────┴─────────┘
```

### Runtime (`src/runtime/`)

| File | Purpose |
|------|---------|
| `sandbox.hpp/cpp` | Linux namespaces (PID, NET, MNT, UTS) + cgroups v2 |
| `agent_process.hpp/cpp` | Agent lifecycle (spawn, kill, list) |

### LLM Service (`agents/llm_service/`)

Python subprocess that handles Gemini API calls. Kernel communicates via stdin/stdout JSON.

```
Kernel (C++) ──JSON──► llm_service.py ──HTTPS──► Gemini API
```

## Data Flow

### Syscall Flow
```
Agent (Python)
    │
    ▼ send(Message)
Unix Socket
    │
    ▼ epoll event
Reactor
    │
    ▼ dispatch
Kernel::handle_message()
    │
    ▼ route by opcode
Syscall Handler (think/spawn/exec/etc)
    │
    ▼ execute
Response
    │
    ▼ send back
Agent receives result
```

### Agent Spawn Flow
```
Client: spawn(name, script, sandboxed=True)
    │
    ▼
Kernel: handle_spawn()
    │
    ▼
AgentManager::spawn_agent()
    │
    ├─► [if sandboxed + root] Sandbox::create_sandbox()
    │       ├─► clone(CLONE_NEWPID | CLONE_NEWNET | ...)
    │       └─► setup_cgroups()
    │
    └─► [else] fork() + exec(python3 script.py)
    │
    ▼
Child process connects back to kernel socket
```

## Permission Model

```
┌─────────────────────────────────────────────┐
│            AgentPermissions                  │
├─────────────────────────────────────────────┤
│ level: UNRESTRICTED|STANDARD|SANDBOXED|...  │
│ allowed_paths: ["/tmp/*", "/home/user/*"]   │
│ blocked_paths: ["~/.ssh/*", "~/.env"]       │
│ blocked_commands: ["rm -rf", "sudo"]        │
│ allowed_domains: ["api.github.com"]         │
│ llm_quota: {max_tokens, max_calls}          │
└─────────────────────────────────────────────┘
```

Every syscall checks permissions before execution.

## IPC (Inter-Agent Communication)

Agents communicate through kernel-mediated mailboxes:

```
Agent A ──SYS_SEND──► Kernel Mailbox[B] ──SYS_RECV──► Agent B
```

- Each agent has a message queue
- Messages are JSON payloads
- Supports: point-to-point, broadcast, name-based addressing

## Multi-Agent Patterns

Clove supports two patterns for multi-agent systems:

### Single-Process (Simulated Agents)

All "agents" are function calls in one process. Simple but no fault isolation.

```
┌──────────────────────────────────────┐
│          Single Python Process       │
│  ┌──────────┐  ┌──────────┐        │
│  │Coordinator│──│Researcher│        │
│  └──────────┘  └──────────┘        │
│       │             │              │
│       └──────┬──────┘              │
│              ▼                      │
│  ┌──────────────────────────────┐  │
│  │    client.think() calls      │  │
│  └──────────────────────────────┘  │
└──────────────────────────────────────┘
              │
              ▼
      Clove Kernel
```

### Multi-Process (Real Agents)

Each agent is a spawned process with IPC messaging. Full fault isolation.

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Coordinator  │  │  Researcher  │  │    Writer    │
│   Process    │  │   Process    │  │   Process    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │    IPC Messages (via kernel)      │
       └─────────────────┼─────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Clove Kernel │
                  │  - Mailboxes │
                  │  - LLM calls │
                  │  - Resources │
                  └──────────────┘
```

**Key Differences:**

| Aspect | Single-Process | Multi-Process |
|--------|---------------|---------------|
| Fault Isolation | None | Full (process boundaries) |
| Resource Limits | Shared | Per-agent (cgroups) |
| Communication | Function calls | IPC messages |
| Complexity | Simple | More setup required |
| Use Case | Prototyping | Production |

**Example: Multi-Process Agent**

```python
# Coordinator spawns agents
client.spawn(name="researcher", script="researcher.py", sandboxed=True)
client.spawn(name="writer", script="writer.py", sandboxed=True)

# Send task to researcher
client.send_message({"task": "research AI"}, to_name="researcher")

# Wait for results
result = client.recv_messages()
```

See [worlds/examples/research_team/](../worlds/examples/research_team/) for a complete comparison.

## Relay Server (`relay/`)

The relay server enables remote connectivity and fleet management.

| File | Purpose |
|------|---------|
| `relay_server.py` | WebSocket hub for kernel connections + REST API host |
| `auth.py` | Token validation, SHA-256 hashing |
| `router.py` | Message routing between agents and kernels |
| `api.py` | REST API endpoints for fleet/agent/token management |
| `fleet.py` | Fleet manager with persistent machine registry |
| `tokens.py` | Token persistence with secure storage |

### Remote Agent Flow

```
Agent (CLI)
    │
    ▼ REST API (8766)
Relay Server
    │
    ▼ WebSocket
Tunnel Client (on kernel)
    │
    ▼ Unix Socket
Clove Kernel
    │
    ▼ Execute syscall
Response flows back
```

### Token Types

| Type | Purpose | Permissions |
|------|---------|-------------|
| `machine` | Kernel registration | Connect, heartbeat, receive commands |
| `agent` | Agent deployment | Target specific machine(s) |
| `admin` | Fleet management | All operations |

## CLI (`cli/`)

Command-line interface for fleet management.

| File | Purpose |
|------|---------|
| `clove.py` | Main entry point with Click groups |
| `config.py` | `~/.clove/config.yaml` management |
| `relay_api.py` | REST API client (sync/async) |
| `commands/deploy.py` | Deploy to Docker/AWS/GCP |
| `commands/status.py` | Fleet status display |
| `commands/machines.py` | Machine management |
| `commands/agent.py` | Agent execution |
| `commands/tokens.py` | Token management |

### Command Flow

```
$ clove agent run script.py --machine m1
    │
    ▼ CLI parses command
RelayAPIClient
    │
    ▼ POST /api/v1/agents/deploy
Relay Server
    │
    ▼ WebSocket message
Kernel (machine m1)
    │
    ▼ Execute agent
Results streamed back
```

## Deployment (`deploy/`)

Infrastructure for deploying Clove to various environments.

| Directory | Purpose |
|-----------|---------|
| `docker/` | Dockerfile, docker-compose, entrypoint |
| `terraform/aws/` | EC2, VPC, security groups, cloud-init |
| `terraform/gcp/` | Compute Engine, firewall, cloud-init |
| `systemd/` | Service files for kernel, tunnel, relay |

### Deployment Flow

```
$ clove deploy aws
    │
    ├─► terraform init && terraform apply
    │       Creates EC2 + networking
    │
    └─► cloud-init executes
            │
            ├─► Install Clove
            ├─► Start kernel (systemd)
            └─► Start tunnel (connects to relay)
```
