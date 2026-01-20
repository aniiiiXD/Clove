# AgentOS Architecture

## Overview

AgentOS is a microkernel for AI agents. It provides OS-level isolation, resource control, and fair scheduling for autonomous agents.

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

## Components

### Kernel (`src/kernel/`)

| File | Purpose |
|------|---------|
| `kernel.hpp/cpp` | Main kernel class, syscall routing, IPC mailboxes |
| `reactor.hpp/cpp` | epoll-based event loop |
| `llm_client.hpp/cpp` | Spawns Python subprocess for LLM calls |
| `permissions.hpp/cpp` | Permission validation (paths, commands, domains) |

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
