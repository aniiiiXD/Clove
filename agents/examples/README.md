# AgentOS Examples

## Quick Start

```bash
# Make sure kernel is running
./build/agentos_kernel

# Run any example
python3 agents/examples/hello_agent.py
```

## Basic Examples

| Example | Description |
|---------|-------------|
| `hello_agent.py` | Basic IPC test - sends echo, gets response |
| `thinking_agent.py` | Interactive LLM chat via SYS_THINK |
| `spawn_test.py` | Spawns a worker agent and communicates with it |
| `worker_agent.py` | Simple agent that can be spawned by others |
| `ipc_demo.py` | Inter-agent messaging (SYS_SEND/SYS_RECV) |

## OS-Level Demos

These demonstrate why AgentOS exists - capabilities that Python frameworks can't provide.

| Demo | What It Shows | Command |
|------|---------------|---------|
| `fault_isolation_demo.py` | CPU hog throttled, memory hog killed, healthy survives | `python3 fault_isolation_demo.py` |
| `security_demo.py` | Fork bomb blocked, network isolated | `sudo python3 security_demo.py` |
| `supervisor_demo.py` | Auto-restart crashed agents with backoff | `python3 supervisor_demo.py` |
| `pipeline_demo.py` | Parser → Reasoner → Verifier with real IPC | `python3 pipeline_demo.py` |
| `llm_contention_demo.py` | Fair LLM scheduling across 5 agents | `python3 llm_contention_demo.py` |

## Individual Agents

### Fault Isolation Agents
| Agent | Purpose |
|-------|---------|
| `cpu_hog_agent.py` | Infinite loop - gets throttled by cgroups |
| `memory_hog_agent.py` | Memory leak - gets OOM killed |
| `healthy_agent.py` | Well-behaved agent - survives failures |

### Security Test Agents
| Agent | Purpose |
|-------|---------|
| `fork_bomb_agent.py` | Attempts fork bomb - blocked by max_pids |
| `network_test_agent.py` | Tests network access - blocked in sandbox |

### Pipeline Agents
| Agent | Purpose |
|-------|---------|
| `parser_agent.py` | Stage 1: Parse natural language to structured |
| `reasoner_agent.py` | Stage 2: Compute results |
| `verifier_agent.py` | Stage 3: Verify correctness |

### Supervisor Agents
| Agent | Purpose |
|-------|---------|
| `supervisor_agent.py` | PID 1 semantics - watches and restarts children |
| `unstable_agent.py` | Crashes randomly for testing supervisor |

### Other
| Agent | Purpose |
|-------|---------|
| `coding_agent.py` | Code generation using LLM |
| `fibonacci_orchestrator.py` | Multi-agent orchestration example |
| `llm_requester_agent.py` | Makes LLM requests for contention testing |

## Running with Full Isolation

Some demos require root for full namespace/cgroup isolation:

```bash
sudo ./build/agentos_kernel  # Start kernel with root
python3 agents/examples/security_demo.py  # Run demo
```

Without root, agents still run in separate processes but resource limits aren't enforced.

## Environment Variables

```bash
export GEMINI_API_KEY="your-key"  # Required for LLM demos
```

Or add to `.env` file in project root.
