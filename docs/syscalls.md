# AgentOS Syscall Reference

## Wire Protocol

```
┌──────────────┬──────────────┬─────────┬───────────────┐
│  Magic (4B)  │ Agent ID (4B)│ Op (1B) │ Payload Len   │
│  0x41474E54  │   uint32     │  uint8  │   uint64 (8B) │
└──────────────┴──────────────┴─────────┴───────────────┘
                    17 bytes total, then payload
```

- **Magic**: `0x41474E54` ("AGNT")
- **Max payload**: 1 MB
- **Socket**: `/tmp/agentos.sock`

---

## Syscall Table

### Core

| Op | Name | Payload | Response |
|----|------|---------|----------|
| `0x00` | NOOP | `string` | Same string (echo) |
| `0xFF` | EXIT | — | Acknowledgment |

### LLM

| Op | Name | Payload | Response |
|----|------|---------|----------|
| `0x01` | THINK | `{"prompt", "image?", "system_instruction?", "thinking_level?", "temperature?", "model?"}` | `{"success", "content", "tokens", "error"}` |

### Filesystem

| Op | Name | Payload | Response |
|----|------|---------|----------|
| `0x02` | EXEC | `{"command", "cwd?", "timeout?"}` | `{"success", "stdout", "stderr", "exit_code"}` |
| `0x03` | READ | `{"path"}` | `{"success", "content", "size"}` |
| `0x04` | WRITE | `{"path", "content", "mode?"}` | `{"success", "bytes_written"}` |

### Agent Management

| Op | Name | Payload | Response |
|----|------|---------|----------|
| `0x10` | SPAWN | `{"name", "script", "sandboxed?", "network?", "limits?"}` | `{"success", "agent_id", "pid"}` |
| `0x11` | KILL | `{"name"}` or `{"id"}` | `{"killed", "agent_id"}` |
| `0x12` | LIST | — | `[{"id", "name", "pid", "state", "uptime_ms"}]` |

### IPC (Inter-Agent Communication)

| Op | Name | Payload | Response |
|----|------|---------|----------|
| `0x20` | SEND | `{"to" or "to_name", "message"}` | `{"success", "delivered_to"}` |
| `0x21` | RECV | `{"max?"}` | `{"success", "count", "messages"}` |
| `0x22` | BROADCAST | `{"message", "include_self?"}` | `{"success", "delivered_count"}` |
| `0x23` | REGISTER | `{"name"}` | `{"success", "agent_id", "name"}` |

### Permissions

| Op | Name | Payload | Response |
|----|------|---------|----------|
| `0x40` | GET_PERMS | — | `{"success", "permissions"}` |
| `0x41` | SET_PERMS | `{"agent_id?", "level?" or "permissions?"}` | `{"success", "agent_id"}` |

**Levels**: `unrestricted`, `standard`, `sandboxed`, `readonly`, `minimal`

### Network

| Op | Name | Payload | Response |
|----|------|---------|----------|
| `0x50` | HTTP | `{"url", "method?", "headers?", "body?", "timeout?"}` | `{"success", "status_code", "body"}` |

---

## Future Syscalls

### State Store (Phase 2)

| Op | Name | Description |
|----|------|-------------|
| `0x30` | STORE | Store key-value pair |
| `0x31` | FETCH | Retrieve value by key |
| `0x32` | DELETE | Delete a key |
| `0x33` | KEYS | List keys with optional prefix |

**Scopes**: `global` (all agents), `agent` (private), `session` (until restart)

### Network Extended

| Op | Name | Description |
|----|------|-------------|
| `0x51` | DOWNLOAD | Download file from URL to path |

### Events (Phase 5)

| Op | Name | Description |
|----|------|-------------|
| `0x60` | SUBSCRIBE | Subscribe to event types |
| `0x61` | UNSUBSCRIBE | Unsubscribe from events |
| `0x62` | POLL_EVENTS | Get pending events |
| `0x63` | EMIT | Emit custom event |

**Event types**: `AGENT_SPAWNED`, `AGENT_EXITED`, `FILE_CHANGED`, `MESSAGE_RECEIVED`, `SYSCALL_BLOCKED`, `RESOURCE_WARNING`, `CUSTOM`

### Remote Tunnel (Phase 6)

| Op | Name | Description |
|----|------|-------------|
| `0x70` | TUNNEL_CONNECT | Connect kernel to relay server |
| `0x71` | TUNNEL_STATUS | Check tunnel connection status |
| `0x72` | TUNNEL_DISCONNECT | Disconnect from relay |

### Task Orchestration (Phase 7)

| Op | Name | Description |
|----|------|-------------|
| `0x80` | TASK_CREATE | Create orchestrated task |
| `0x81` | TASK_ASSIGN | Assign agent to task |
| `0x82` | TASK_STATUS | Get task status |
| `0x83` | TASK_COMPLETE | Mark task complete |
| `0x84` | TASK_LIST | List active tasks |

### Metrics & Quotas (Phase 8)

| Op | Name | Description |
|----|------|-------------|
| `0x90` | METRICS | Get own resource metrics |
| `0x91` | METRICS_ALL | Get all agents' metrics (privileged) |
| `0x92` | SET_QUOTA | Set resource quota for agent |

---

## Status Codes

| Code | Name |
|------|------|
| `0x00` | OK |
| `0x01` | ERROR |
| `0x02` | INVALID_MSG |
| `0x03` | NOT_FOUND |
| `0x04` | TIMEOUT |

---

## Python SDK

```python
from agentos import AgentOSClient

with AgentOSClient() as c:
    c.echo("ping")                              # NOOP
    c.think("What is 2+2?")                     # THINK
    c.exec("ls -la")                            # EXEC
    c.read_file("/tmp/test.txt")                # READ
    c.write_file("/tmp/out.txt", "data")        # WRITE
    c.spawn("worker", "print('hi')")            # SPAWN
    c.kill(name="worker")                       # KILL
    c.list_agents()                             # LIST
    c.register_name("orchestrator")             # REGISTER
    c.send_message({"task": "go"}, to_name="worker")  # SEND
    c.recv_messages()                                  # RECV
    c.broadcast({"event": "done"})              # BROADCAST
    c.get_permissions()                         # GET_PERMS
    c.set_permissions(level="sandboxed")        # SET_PERMS
    c.http("https://api.example.com/data")      # HTTP
```
