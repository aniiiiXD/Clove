# CLOVE System Design - C++ Kernel Documentation

> Comprehensive technical documentation explaining the CLOVE kernel architecture, component responsibilities, and code organization.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Directory Structure](#2-directory-structure)
3. [Core Components](#3-core-components)
4. [File-by-File Reference](#4-file-by-file-reference)
5. [System Interactions](#5-system-interactions)
6. [Design Patterns](#6-design-patterns)
7. [Configuration](#7-configuration)
8. [Thread Safety](#8-thread-safety)

---

## 1. Executive Summary

CLOVE (Clove Lightweight Operating Virtualization Environment) is a **microkernel-based operating system** designed specifically for managing intelligent agents. The C++ kernel implements:

| Feature | Implementation |
|---------|----------------|
| **Event-Driven I/O** | Linux epoll-based reactor pattern |
| **Process Isolation** | Linux namespaces (PID, NET, MNT, UTS) |
| **Resource Limits** | cgroups v2 (memory, CPU, PIDs) |
| **IPC** | Unix domain sockets with binary protocol |
| **Permission System** | Fine-grained access control with quotas |
| **LLM Integration** | Subprocess-based Gemini API calls |
| **World Simulation** | Multi-world engine with VFS, network mock, chaos injection |

---

## 2. Directory Structure

```
/home/anixd/Documents/CLOVE/src/
├── main.cpp                    # Entry point - kernel startup
│
├── kernel/                     # Core kernel components
│   ├── kernel.cpp             # Main orchestrator
│   ├── reactor.cpp            # epoll-based event loop
│   ├── world_engine.cpp       # Multi-world simulation
│   ├── permissions.cpp        # Access control system
│   ├── virtual_fs.cpp         # In-memory filesystem
│   ├── audit_log.cpp          # Security logging
│   ├── execution_log.cpp      # Trace recording/replay
│   ├── tunnel_client.cpp      # Remote agent connectivity
│   ├── llm_client.cpp         # Gemini LLM integration
│   └── metrics/
│       └── metrics.cpp        # System metrics collection
│
├── runtime/                    # Process management
│   ├── agent_process.cpp      # Agent lifecycle management
│   └── sandbox.cpp            # Namespace/cgroup isolation
│
├── ipc/                        # Inter-process communication
│   └── socket_server.cpp      # Unix socket server
│
└── util/
    └── logger.cpp             # Logging utilities
```

---

## 3. Core Components

### 3.1 Component Interaction Diagram

```
                    ┌─────────────────────────────────────────┐
                    │              KERNEL (kernel.cpp)         │
                    │  Orchestrates all subsystems             │
                    └─────────────────┬───────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│    REACTOR    │           │ SOCKET_SERVER │           │ AGENT_MANAGER │
│  (reactor.cpp)│◄─────────►│(socket_server)│           │(agent_process)│
│               │           │               │           │               │
│  epoll loop   │           │  IPC layer    │           │  lifecycle    │
└───────────────┘           └───────────────┘           └───────┬───────┘
                                                                │
                                                                ▼
                                                        ┌───────────────┐
                                                        │    SANDBOX    │
                                                        │ (sandbox.cpp) │
                                                        │               │
                                                        │  namespaces   │
                                                        │  cgroups v2   │
                                                        └───────────────┘
```

### 3.2 Component Summary Table

| Component | File | Purpose |
|-----------|------|---------|
| **Kernel** | `kernel.cpp` | Central orchestrator, message dispatch, subsystem init |
| **Reactor** | `reactor.cpp` | epoll-based event loop, non-blocking I/O |
| **SocketServer** | `socket_server.cpp` | Unix socket IPC, message framing |
| **AgentProcess** | `agent_process.cpp` | Agent lifecycle (start/stop/pause/resume) |
| **AgentManager** | `agent_process.cpp` | Multi-agent management, restart policies |
| **Sandbox** | `sandbox.cpp` | Process isolation via namespaces/cgroups |
| **Permissions** | `permissions.cpp` | Access control, path/command/domain checks |
| **VirtualFS** | `virtual_fs.cpp` | In-memory filesystem for testing |
| **WorldEngine** | `world_engine.cpp` | Multi-world simulation environments |
| **AuditLog** | `audit_log.cpp` | Security event logging |
| **ExecutionLog** | `execution_log.cpp` | Syscall recording and replay |
| **Metrics** | `metrics.cpp` | CPU/memory/IO statistics from /proc |
| **TunnelClient** | `tunnel_client.cpp` | Remote agent connectivity |
| **LLMClient** | `llm_client.cpp` | Gemini API integration |

---

## 4. File-by-File Reference

### 4.1 `main.cpp` - Entry Point

**Purpose**: Kernel entry point with startup sequence and banner display.

**Key Functions**:
```cpp
void print_banner()              // ASCII art logo
void print_startup_sequence()    // Animated spinner during init
void print_status_box()          // Show socket, sandbox, LLM status
void print_ready_message()       // Final "Kernel ready" message
int main()                       // Initialize kernel and run
```

**Flow**:
1. Print banner
2. Initialize kernel subsystems
3. Print status
4. Run event loop until shutdown

---

### 4.2 `kernel/kernel.cpp` - Main Kernel

**Purpose**: Central orchestrator coordinating all subsystems.

**Key Responsibilities**:
- Initialize all subsystems (Reactor, SocketServer, AgentManager, etc.)
- Handle signal management (SIGINT, SIGTERM)
- Process IPC messages from agents
- Manage the main event loop
- Coordinate with LLM service and tunnel client

**Key Classes**:
```cpp
struct Kernel::Config {
    std::string socket_path = "/tmp/clove.sock";
    bool enable_sandboxing = true;
    std::string llm_model = "gemini-1.5-pro";
    std::string gemini_api_key = "";
};
```

**Key Methods**:
```cpp
bool init()                      // Initialize all subsystems
void run()                       // Main event loop (calls reactor.run())
void shutdown()                  // Graceful shutdown
Message handle_message(Message&) // Process agent syscalls (READ, WRITE, EXEC, etc.)
```

**Message Handling**:
The `handle_message()` method routes syscalls based on opcode:
- `READ` → Read file (real or virtual)
- `WRITE` → Write file
- `EXEC` → Execute command
- `THINK` → LLM inference
- `SPAWN` → Create child agent
- `SEND`/`RECV` → IPC messaging
- `STORE`/`FETCH` → State storage

---

### 4.3 `kernel/reactor.cpp` - Event Loop

**Purpose**: Non-blocking, event-driven I/O using Linux epoll.

**Key Responsibilities**:
- Manage file descriptors for agents and services
- Poll for I/O readiness (EPOLLIN, EPOLLOUT)
- Dispatch events to registered callbacks
- Handle graceful shutdown with 100ms polling timeout

**Key Methods**:
```cpp
bool init()                            // Create epoll instance
bool add(int fd, uint32_t events,      // Add fd to reactor with callback
         EventCallback callback)
bool modify(int fd, uint32_t events)   // Change event mask
bool remove(int fd)                    // Remove fd from reactor
int poll(int timeout_ms)               // Wait for events
void run()                             // Main event loop
void stop()                            // Signal shutdown
```

**Implementation Details**:
- Uses `epoll_create1(EPOLL_CLOEXEC)` for FD-safe epoll
- Max 64 events per poll cycle
- 100ms timeout for responsiveness
- Callback map: `std::unordered_map<int, EventCallback>`

---

### 4.4 `ipc/socket_server.cpp` - IPC Layer

**Purpose**: Bi-directional communication between kernel and agents.

**Key Responsibilities**:
- Accept incoming agent connections via Unix domain sockets
- Serialize/deserialize binary IPC messages
- Buffer send/receive data per client
- Assign unique agent IDs on connection

**Key Classes**:
```cpp
struct ClientConnection {
    int fd;
    uint32_t agent_id;
    std::vector<uint8_t> recv_buffer;
    std::vector<uint8_t> send_buffer;
};
```

**Key Methods**:
```cpp
bool init(const std::string& socket_path)  // Bind and listen
int accept_connection()                     // Accept new agent
bool handle_client(int client_fd)           // Read incoming data
void process_messages(ClientConnection&)    // Parse complete messages
bool send_response(int client_fd, Message&) // Queue response
bool flush_client(int client_fd)            // Write queued data
void remove_client(int client_fd)           // Clean up
```

**Protocol Format**:
- Binary framed: 4-byte length header + payload
- Messages parsed using `Message::deserialize()`
- Responses queued and flushed asynchronously

---

### 4.5 `runtime/agent_process.cpp` - Agent Lifecycle

**Purpose**: Lifecycle management of agent processes.

**Key Classes**:

```cpp
enum class AgentState {
    CREATED,    // Config set, not started
    STARTING,   // In startup process
    RUNNING,    // Active and responding
    PAUSED,     // Suspended via SIGSTOP
    STOPPING,   // Shutdown in progress
    STOPPED,    // Cleanly exited
    FAILED      // Crashed or killed
};

class AgentProcess {
    // Single agent wrapper
};

class AgentManager {
    // Manages multiple agents with restart policies
};
```

**AgentProcess Methods**:
```cpp
bool start()                   // Launch in sandbox
bool stop(int timeout_ms)      // Graceful shutdown → SIGTERM → SIGKILL
bool restart()                 // Stop then start
bool pause()                   // SIGSTOP
bool resume()                  // SIGCONT
int wait()                     // Wait for exit
bool is_running() const        // Check if alive
AgentMetrics get_metrics()     // Get resource usage
```

**AgentManager Methods**:
```cpp
std::shared_ptr<AgentProcess> spawn_agent(AgentConfig)  // Create & start
bool kill_agent(const std::string& name)                // Kill by name
bool pause_agent(const std::string& name)               // Pause by name
bool resume_agent(const std::string& name)              // Resume by name
void reap_and_restart_agents()                          // Check dead, restart
void process_pending_restarts()                         // Execute scheduled restarts
```

**Restart Policy**:
```cpp
enum class RestartPolicy {
    ALWAYS,      // Restart regardless of exit code
    ON_FAILURE,  // Restart if exit != 0
    NEVER        // Never restart
};

struct RestartConfig {
    RestartPolicy policy;
    uint32_t max_restarts = 5;
    uint32_t restart_window_sec = 60;
    uint32_t backoff_initial_ms = 100;
    double backoff_multiplier = 2.0;
    uint32_t backoff_max_ms = 30000;
};
```

---

### 4.6 `runtime/sandbox.cpp` - Process Isolation

**Purpose**: Process isolation using Linux namespaces and cgroups v2.

**Isolation Mechanisms**:

| Mechanism | Clone Flag | Purpose |
|-----------|------------|---------|
| PID Namespace | `CLONE_NEWPID` | Isolate process IDs |
| Mount Namespace | `CLONE_NEWNS` | Isolate filesystem mounts |
| UTS Namespace | `CLONE_NEWUTS` | Isolate hostname |
| Network Namespace | `CLONE_NEWNET` | Isolate network interfaces |
| cgroups v2 | (controller files) | Resource limits |

**Key Classes**:
```cpp
struct IsolationStatus {
    bool fully_isolated = true;
    bool pid_namespace = false;
    bool mnt_namespace = false;
    bool uts_namespace = false;
    bool net_namespace = false;
    bool cgroups_available = false;
    bool memory_limit_applied = false;
    bool cpu_quota_applied = false;
    bool pids_limit_applied = false;
    std::string degraded_reason;
};

class Sandbox {
    // Single sandbox instance
};

class SandboxManager {
    // Global sandbox lifecycle management
};
```

**Key Methods**:
```cpp
bool create()               // Initialize cgroups directory
bool start()                // clone() or fork() the process
bool stop(int timeout_ms)   // Graceful → SIGTERM → SIGKILL
bool pause()                // SIGSTOP
bool resume()               // SIGCONT
bool is_running() const     // Check via kill(pid, 0)
IsolationStatus get_isolation_status()  // What's actually enforced
```

**Graceful Degradation**:
If `clone()` fails (requires CAP_SYS_ADMIN), falls back to `fork()`:
```cpp
child_pid_ = clone(child_func, stack_top, clone_flags, ...);
if (child_pid_ < 0) {
    spdlog::warn("DEGRADED: clone() failed, falling back to fork()");
    child_pid_ = fork();  // Continue with reduced isolation
    isolation_status_.degraded_reason = "clone() failed";
}
```

---

### 4.7 `kernel/permissions.cpp` - Access Control

**Purpose**: Fine-grained access control for agent operations.

**Permission Levels**:
```cpp
enum class PermissionLevel {
    UNRESTRICTED,  // No restrictions
    STANDARD,      // Limited: no spawn, no HTTP
    SANDBOXED,     // Read /tmp/*, /home/*; write only /tmp/*
    READONLY,      // Read-only access
    MINIMAL        // Think only (for testing)
};
```

**AgentPermissions Fields**:
```cpp
struct AgentPermissions {
    // Capabilities
    bool can_exec = false;
    bool can_read = false;
    bool can_write = false;
    bool can_think = false;
    bool can_spawn = false;
    bool can_http = false;

    // Path restrictions (glob patterns)
    std::vector<std::string> read_paths;   // e.g., "/tmp/*", "/home/**"
    std::vector<std::string> write_paths;
    std::vector<std::string> blocked_paths;

    // Command restrictions
    std::vector<std::string> allowed_commands;
    std::vector<std::string> blocked_commands;  // Substring match

    // Network restrictions
    std::vector<std::string> allowed_domains;  // "*" = all

    // LLM quotas
    uint32_t llm_max_tokens = 0;     // 0 = unlimited
    uint32_t llm_max_calls = 0;
    uint32_t llm_tokens_used = 0;
    uint32_t llm_calls_made = 0;
};
```

**Key Methods**:
```cpp
bool can_read_path(const std::string& path)           // fnmatch check
bool can_write_path(const std::string& path)          // fnmatch check
bool can_execute_command(const std::string& cmd)      // Substring match
bool can_access_domain(const std::string& domain)     // Wildcard match
bool can_use_llm(uint32_t estimated_tokens)          // Quota check
void record_llm_usage(uint32_t tokens)               // Track usage
```

---

### 4.8 `kernel/virtual_fs.cpp` - Virtual Filesystem

**Purpose**: In-memory filesystem for world simulation and testing.

**Key Classes**:
```cpp
struct VirtualFile {
    std::string content;
    std::string mode;  // "r" = read-only, "rw" = read-write
};

class VirtualFilesystem {
    std::unordered_map<std::string, VirtualFile> files_;
    std::vector<std::regex> readonly_patterns_;
    std::vector<std::regex> writable_patterns_;
    std::vector<std::regex> intercept_patterns_;
};
```

**Key Methods**:
```cpp
bool exists(const std::string& path)
std::optional<std::string> read(const std::string& path)
bool write(const std::string& path, const std::string& content, bool append)
bool remove(const std::string& path)
std::vector<std::string> list(const std::string& pattern)
bool should_intercept(const std::string& path)  // VFS handles this path?
```

**Configuration (JSON)**:
```json
{
  "initial_files": {
    "/etc/config.json": "{\"debug\": true}",
    "/data/cache.txt": {"content": "cached data", "mode": "r"}
  },
  "readonly_patterns": ["/etc/*"],
  "writable_patterns": ["/tmp/*", "/home/*"],
  "intercept_patterns": ["/virtual/*"]
}
```

---

### 4.9 `kernel/world_engine.cpp` - World Simulation

**Purpose**: Multi-world simulation with virtual environments for testing.

**Key Components**:

```cpp
class World {
    WorldId id_;
    std::string name_;
    VirtualFilesystem vfs_;
    NetworkMock network_mock_;
    ChaosEngine chaos_;
    std::set<uint32_t> agents_;
    WorldMetrics metrics_;
};

class WorldEngine {
    std::unordered_map<WorldId, std::unique_ptr<World>> worlds_;
    std::unordered_map<uint32_t, WorldId> agent_to_world_;
};
```

**World Features**:

| Feature | Class | Purpose |
|---------|-------|---------|
| Virtual FS | `VirtualFilesystem` | Mock filesystem |
| Network Mock | `NetworkMock` | Mock HTTP responses |
| Chaos Engine | `ChaosEngine` | Inject failures |
| Metrics | `WorldMetrics` | Track operations |

**ChaosEngine Event Types**:
- `disk_fail` - Fail disk operations
- `disk_full` - Simulate disk full
- `network_partition` - Block network
- `slow_io` - Add latency

**Key Methods**:
```cpp
std::optional<WorldId> create_world(const std::string& name, json config)
bool destroy_world(const WorldId& id)
std::vector<json> list_worlds()
bool join_world(uint32_t agent_id, const WorldId& world_id)
bool leave_world(uint32_t agent_id)
bool inject_event(const WorldId& id, const std::string& event_type, json params)
json snapshot_world(const WorldId& id)
std::optional<WorldId> restore_world(const std::string& snapshot_json)
```

---

### 4.10 `kernel/audit_log.cpp` - Security Logging

**Purpose**: Security and compliance event logging.

**Audit Categories**:
```cpp
enum class AuditCategory {
    SECURITY,         // Permission violations
    AGENT_LIFECYCLE,  // Start/stop/crash
    IPC,              // Message exchange
    STATE_STORE,      // Store/fetch operations
    RESOURCE,         // Resource allocation
    SYSCALL,          // Individual syscalls
    NETWORK,          // HTTP operations
    WORLD             // World operations
};
```

**Key Methods**:
```cpp
void log(AuditCategory category,
         const std::string& event_type,
         uint32_t agent_id,
         const json& details,
         bool success)

std::vector<AuditLogEntry> get_entries(
    AuditCategory* category,  // Filter by category
    uint32_t* agent_id,       // Filter by agent
    uint64_t since_id,        // Pagination
    size_t limit)

std::string export_jsonl(size_t limit)  // Export for analysis
```

---

### 4.11 `kernel/execution_log.cpp` - Trace Recording

**Purpose**: Record agent execution for debugging and replay.

**Recording States**:
```cpp
enum class RecordingState {
    IDLE,       // Not recording
    RECORDING,  // Actively recording
    PAUSED      // Recording paused
};
```

**Key Methods**:
```cpp
bool start_recording()
bool stop_recording()
bool pause_recording()
bool resume_recording()

void log_syscall(uint32_t agent_id,
                 uint8_t opcode,
                 const std::string& payload,
                 const std::string& response,
                 uint64_t duration_us,
                 bool success)

bool start_replay()
std::optional<SyscallEntry> next_replay_entry()
std::string export_recording()
bool import_recording(const std::string& json)
```

---

### 4.12 `kernel/metrics/metrics.cpp` - System Metrics

**Purpose**: Real-time system and process monitoring.

**Metrics Types**:
```cpp
struct SystemMetrics {
    double cpu_percent;
    double load_avg[3];
    uint64_t mem_total, mem_available, mem_used;
    uint64_t disk_read_bytes, disk_write_bytes;
    uint64_t net_rx_bytes, net_tx_bytes;
};

struct ProcessMetrics {
    pid_t pid;
    uint64_t rss_bytes, vsz_bytes;
    double cpu_percent;
    uint64_t io_read_bytes, io_write_bytes;
};

struct CgroupMetrics {
    uint64_t memory_current, memory_limit;
    uint64_t cpu_usage_usec;
    uint32_t pids_current, pids_limit;
};

struct AgentMetrics {
    // Combines process + cgroup + kernel stats
};
```

**Data Sources**:
- `/proc/stat` → CPU usage
- `/proc/meminfo` → Memory stats
- `/proc/diskstats` → Disk I/O
- `/proc/net/dev` → Network I/O
- `/proc/[pid]/stat` → Process CPU/memory
- `/proc/[pid]/io` → Process I/O
- `/sys/fs/cgroup/` → Cgroup limits

**Key Methods**:
```cpp
SystemMetrics collect_system()
std::optional<ProcessMetrics> collect_process(pid_t pid)
CgroupMetrics collect_cgroup(const std::string& cgroup_path)
AgentMetrics collect_agent(uint32_t agent_id, pid_t pid, ...)
```

---

### 4.13 `kernel/tunnel_client.cpp` - Remote Connectivity

**Purpose**: Remote agent connectivity via relay tunnel.

**Key Classes**:
```cpp
enum class TunnelEventType {
    AGENT_CONNECTED,
    AGENT_DISCONNECTED,
    SYSCALL,
    DISCONNECTED,
    RECONNECTED,
    ERROR
};

struct TunnelEvent {
    TunnelEventType type;
    uint32_t agent_id;
    std::string data;
};
```

**Key Methods**:
```cpp
bool init(const std::string& scripts_dir)  // Start subprocess
bool configure(const TunnelConfig& config) // Set relay URL, token
bool connect()
void disconnect()
bool send_response(uint32_t agent_id, uint8_t opcode, const std::vector<uint8_t>& payload)
std::vector<TunnelEvent> poll_events()
TunnelStatus get_status() const
```

---

### 4.14 `kernel/llm_client.cpp` - LLM Integration

**Purpose**: Integration with Gemini LLM API.

**Key Classes**:
```cpp
struct LLMResponse {
    std::string content;
    uint32_t prompt_tokens;
    uint32_t completion_tokens;
    bool success;
    std::string error;
};

struct ChatMessage {
    std::string role;     // "user" or "assistant"
    std::string content;
};
```

**Key Methods**:
```cpp
bool is_configured() const                         // API key set?
LLMResponse complete(const std::string& prompt)    // Single completion
LLMResponse chat(const std::vector<ChatMessage>&)  // Chat mode
LLMResponse complete_with_options(const std::string& json)  // Custom
```

**Configuration**:
- Model: `gemini-1.5-pro` (default)
- Temperature: 0.7
- Max tokens: 2048
- API key: `GEMINI_API_KEY` or `GOOGLE_API_KEY` env var

---

### 4.15 `util/logger.cpp` - Logging

**Purpose**: Structured logging via spdlog.

**Key Methods**:
```cpp
void init_logger()                                     // Initialize
void set_log_level(spdlog::level::level_enum level)   // Set level
```

**Log Levels**:
- `trace` - Low-level details
- `debug` - Development info
- `info` - Normal operations
- `warn` - Degraded operation
- `error` - Failures

---

## 5. System Interactions

### 5.1 Agent Startup Sequence

```
main()
  │
  ├─ Kernel::init()
  │   ├─ reactor_.init()          [epoll_create1]
  │   ├─ socket_server_.init()    [bind Unix socket]
  │   └─ ... other subsystems
  │
  └─ Kernel::run()
      └─ reactor_.run()           [event loop]

When spawn_agent() is called:
  │
  ├─ AgentManager::spawn_agent(config)
  │   ├─ Create AgentProcess
  │   ├─ Create Sandbox with limits
  │   └─ Sandbox::start()
  │       ├─ clone() with namespace flags
  │       ├─ Add child to cgroup
  │       └─ execvp() agent script
  │
  └─ Agent connects to Unix socket
      ├─ SocketServer::accept_connection()
      ├─ Assign unique agent_id
      └─ Reactor::add(client_fd, EPOLLIN)
```

### 5.2 Syscall Processing Flow

```
Agent sends Message via socket
         │
         ▼
SocketServer::handle_client()
         │
         ▼
SocketServer::process_messages()
    ├─ Deserialize binary message
    └─ Call registered handler
         │
         ▼
Kernel::handle_message()
    ├─ Check permissions
    ├─ Route by opcode (READ/WRITE/EXEC/THINK/etc.)
    ├─ Execute operation
    ├─ Log to audit if enabled
    └─ Queue response
         │
         ▼
Reactor detects EPOLLOUT
         │
         ▼
SocketServer::flush_client()
    └─ Write response to socket
```

### 5.3 Agent Crash & Recovery

```
Agent process exits (crash/exception)
         │
         ▼
AgentManager::reap_and_restart_agents()  [called periodically]
    ├─ Detect dead via is_running()
    ├─ Check restart policy
    ├─ Calculate backoff delay
    └─ Queue PendingRestart
         │
         ▼
AgentManager::process_pending_restarts()
    ├─ Check if scheduled time reached
    ├─ spawn_agent() with same config
    ├─ Track consecutive failures
    └─ Escalate if max_restarts exceeded
```

---

## 6. Design Patterns

### 6.1 Event-Driven (Reactor Pattern)

```cpp
while (running_) {
    int n = poll(100);  // 100ms timeout
    for (int i = 0; i < n; i++) {
        callbacks_[fd](fd, events);  // Dispatch to callback
    }
}
```

### 6.2 Graceful Degradation

```cpp
// If clone() fails, fall back to fork()
if (child_pid_ < 0) {
    spdlog::warn("DEGRADED: clone() failed");
    child_pid_ = fork();  // Continue with reduced isolation
    isolation_status_.degraded_reason = "clone() not available";
}
```

### 6.3 Exponential Backoff

```cpp
uint32_t calculate_backoff(uint32_t consecutive_failures) {
    uint32_t delay = config.backoff_initial_ms;
    for (uint32_t i = 0; i < consecutive_failures; ++i) {
        delay *= config.backoff_multiplier;
        if (delay >= config.backoff_max_ms) return config.backoff_max_ms;
    }
    return delay;
}
```

### 6.4 RAII Cleanup

```cpp
~Sandbox() {
    if (state_ == RUNNING) stop();
    destroy();  // Cleanup cgroups
}

~SocketServer() {
    stop();
    unlink(socket_path_);
}
```

---

## 7. Configuration

### 7.1 Kernel Config

```cpp
struct Kernel::Config {
    std::string socket_path = "/tmp/clove.sock";
    bool enable_sandboxing = true;
    std::string llm_model = "gemini-1.5-pro";
    std::string gemini_api_key = "";  // From env
};
```

### 7.2 Agent Config

```cpp
struct AgentConfig {
    std::string name;
    std::string script_path;
    std::string socket_path;
    bool sandboxed = true;

    struct Limits {
        uint64_t memory_limit_bytes = 512 * 1024 * 1024;  // 512MB
        uint64_t cpu_quota_us = 100000;   // 100ms per period
        uint64_t cpu_period_us = 100000;  // 100ms period
        uint32_t max_pids = 256;
    } limits;

    struct RestartConfig {
        RestartPolicy policy = ALWAYS;
        uint32_t max_restarts = 5;
        uint32_t restart_window_sec = 60;
        uint32_t backoff_initial_ms = 100;
        double backoff_multiplier = 2.0;
        uint32_t backoff_max_ms = 30000;
    } restart;
};
```

### 7.3 World Config (JSON)

```json
{
  "name": "test_world",
  "virtual_filesystem": {
    "initial_files": {
      "/etc/config.json": "{\"debug\": true}"
    },
    "readonly_patterns": ["/etc/*"],
    "writable_patterns": ["/tmp/*"]
  },
  "network": {
    "mode": "mock",
    "mock_responses": {
      "https://api.example.com/*": {"status": 200, "body": "{}"}
    }
  },
  "chaos": {
    "enabled": true,
    "failure_rate": 0.05,
    "latency": {"min_ms": 10, "max_ms": 100}
  }
}
```

---

## 8. Thread Safety

### 8.1 Architecture

The kernel is **fundamentally single-threaded** with exceptions:

| Component | Threading | Notes |
|-----------|-----------|-------|
| Kernel | Single-threaded | Event loop runs in main thread |
| Reactor | Single-threaded | All I/O in main thread |
| SocketServer | Single-threaded | Part of event loop |
| TunnelClient | Reader thread | Background subprocess I/O |
| LLMClient | Synchronous | Blocking subprocess calls |

### 8.2 Mutexes

Components with internal mutexes for thread-safe access:

- `WorldEngine::worlds_mutex_`
- `World::mutex_`
- `VirtualFilesystem::mutex_`
- `NetworkMock::mutex_`
- `ChaosEngine::mutex_`
- `AuditLogger::mutex_`
- `ExecutionLogger::mutex_`
- `TunnelClient::event_queue_mutex_`, `response_mutex_`, `agents_mutex_`

---

## Quick Reference Card

| Need to... | Look at... |
|------------|------------|
| Understand main loop | `reactor.cpp` |
| Debug IPC issues | `socket_server.cpp` |
| Fix agent crashes | `agent_process.cpp`, `sandbox.cpp` |
| Add new permission | `permissions.cpp` |
| Mock filesystem | `virtual_fs.cpp` |
| Create test world | `world_engine.cpp` |
| Find security logs | `audit_log.cpp` |
| Replay execution | `execution_log.cpp` |
| Check resource usage | `metrics/metrics.cpp` |
| Debug remote agents | `tunnel_client.cpp` |
| LLM integration | `llm_client.cpp` |

---

*This documentation covers CLOVE kernel v1.0. For SDK documentation, see the Python client in `/agents/clove_sdk/`.*
