# Clove Test Suite

Comprehensive test suite for verifying all Clove kernel syscalls and features.

## Prerequisites

1. **Build the kernel:**
   ```bash
   cd /path/to/clove
   mkdir -p build && cd build
   cmake .. && make -j$(nproc)
   ```

2. **Start the kernel:**
   ```bash
   ./build/clove_kernel
   ```

3. **Install Python SDK:**
   ```bash
   cd agents/python_sdk
   pip install -e .
   ```

## Running Tests

### Run All Tests
```bash
python test_suite/run_all.py
```

### Run Individual Tests
```bash
python test_suite/01_connection.py
python test_suite/12_pause_resume.py
# etc.
```

## Test Coverage

| Test | File | Description | Syscalls Tested |
|------|------|-------------|-----------------|
| 01 | `01_connection.py` | Basic kernel connection | NOOP |
| 02 | `02_file_operations.py` | File read/write | READ, WRITE |
| 03 | `03_llm_query.py` | LLM integration | THINK |
| 04 | `04_ipc.py` | Inter-agent messaging | SEND, RECV, BROADCAST, REGISTER |
| 05 | `05_shell_exec.py` | Shell command execution | EXEC |
| 06 | `06_agent_management.py` | Agent lifecycle | SPAWN, KILL, LIST |
| 07 | `07_http_request.py` | HTTP requests | HTTP |
| 08 | `08_permissions.py` | Permission system | GET_PERMS, SET_PERMS |
| 09 | `09_events.py` | Pub/Sub events | SUBSCRIBE, UNSUBSCRIBE, POLL_EVENTS, EMIT |
| 10 | `10_state_store.py` | Key-value storage | STORE, FETCH, DELETE, KEYS |
| 11 | `11_metrics.py` | System/agent metrics | METRICS_SYSTEM, METRICS_AGENT, METRICS_ALL_AGENTS, METRICS_CGROUP |
| 12 | `12_pause_resume.py` | Agent pause/resume | PAUSE, RESUME |
| 13 | `13_audit_logging.py` | Audit log system | GET_AUDIT_LOG, SET_AUDIT_CONFIG |
| 14 | `14_execution_replay.py` | Execution recording | RECORD_START, RECORD_STOP, RECORD_STATUS, REPLAY_START, REPLAY_STATUS |

## Test Details

### 01 - Basic Connection
- Connects to kernel via Unix socket
- Sends NOOP (echo) message
- Verifies response

### 02 - File Operations
- Tests READ syscall for file reading
- Tests WRITE syscall for file creation/modification
- Verifies file contents

### 03 - LLM Query
- Sends prompt to LLM via THINK syscall
- Tests with optional parameters (system_instruction, temperature)
- Verifies response structure

### 04 - Inter-Process Communication
- Tests agent name registration
- Tests direct messaging between agents
- Tests broadcast messaging
- Verifies message delivery

### 05 - Shell Execution
- Tests EXEC syscall for shell commands
- Verifies stdout/stderr capture
- Tests timeout handling

### 06 - Agent Management
- Tests SPAWN syscall for agent creation
- Tests LIST syscall for agent enumeration
- Tests KILL syscall for agent termination
- Verifies agent lifecycle

### 07 - HTTP Requests
- Tests HTTP GET/POST requests
- Tests custom headers
- Tests timeout handling

### 08 - Permissions
- Tests permission levels (unrestricted, standard, sandboxed, readonly, minimal)
- Tests permission querying
- Tests permission modification

### 09 - Events (Pub/Sub)
- Tests event subscription
- Tests event emission
- Tests event polling
- Tests event types (AGENT_SPAWNED, CUSTOM, etc.)

### 10 - State Store
- Tests key-value storage with STORE
- Tests value retrieval with FETCH
- Tests key deletion with DELETE
- Tests key listing with KEYS
- Tests scopes (global, agent, session)
- Tests TTL expiration

### 11 - Metrics System
- Tests system-wide metrics (CPU, memory, disk, network)
- Tests per-agent metrics
- Tests cgroup metrics for sandboxed processes

### 12 - Pause/Resume
- Spawns a worker agent
- Pauses agent with PAUSE (SIGSTOP)
- Verifies agent is paused (state check)
- Resumes agent with RESUME (SIGCONT)
- Verifies agent continues execution

### 13 - Audit Logging
- Tests GET_AUDIT_LOG for retrieving entries
- Tests SET_AUDIT_CONFIG for configuration
- Tests category filtering (AGENT_LIFECYCLE, SECURITY, etc.)
- Tests agent_id filtering
- Tests pagination with since_id
- Validates entry structure

### 14 - Execution Recording & Replay
- Tests RECORD_START to begin recording
- Tests recording configuration (include_think, include_http, filter_agents)
- Generates syscalls to record
- Tests RECORD_STOP to end recording
- Tests RECORD_STATUS with export
- Tests REPLAY_START to begin replay
- Tests REPLAY_STATUS to check progress

## Expected Output

Successful run:
```
============================================================
           CLOVE TEST SUITE
============================================================

  ✅ PASS - Basic Connection
  ✅ PASS - File Operations
  ✅ PASS - LLM Query
  ✅ PASS - Inter-Process Communication
  ✅ PASS - Shell Execution
  ✅ PASS - Agent Management
  ✅ PASS - HTTP Requests
  ✅ PASS - Permission System
  ✅ PASS - Event System (Pub/Sub)
  ✅ PASS - State Store
  ✅ PASS - Metrics System
  ✅ PASS - Pause/Resume
  ✅ PASS - Audit Logging
  ✅ PASS - Execution Recording & Replay

============================================================
  Results: 14 passed, 0 failed, 0 skipped
============================================================
```

## Troubleshooting

### "Cannot connect to kernel"
- Ensure kernel is running: `./build/clove_kernel`
- Check socket exists: `ls -la /tmp/clove.sock`

### "ModuleNotFoundError: clove_sdk"
- Install SDK: `pip install -e agents/python_sdk`

### Tests timeout
- Some tests spawn agents that take time
- Increase timeout in run_all.py if needed

### Permission errors
- Run with appropriate permissions
- Check file/directory permissions for test artifacts

## Adding New Tests

1. Create `NN_feature_name.py` following numbering convention
2. Use the standard test structure:
   ```python
   #!/usr/bin/env python3
   """Test NN: Feature - Description"""
   import sys
   import os
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents', 'python_sdk'))
   from clove_sdk import CloveClient

   def main():
       print("=== Test NN: Feature ===\n")

       if not os.path.exists('/tmp/clove.sock'):
           print("SKIP - Kernel not running")
           return 0

       try:
           with CloveClient() as client:
               # Test implementation
               print("  PASSED\n")
               return 0
       except Exception as e:
           print(f"ERROR - {e}")
           return 1

   if __name__ == "__main__":
       exit(main())
   ```
3. Add test to `TESTS` list in `run_all.py`
4. Update this README

## Syscall Reference

See [docs/syscalls.md](../docs/syscalls.md) for complete syscall documentation.
