# Getting Started with Clove

## Prerequisites

- Linux (Ubuntu 22.04+ / Debian 12+)
- GCC 11+ with C++23 support
- CMake 3.20+
- Python 3.10+
- Root access (optional, for full sandbox isolation)

## Quick Install

```bash
# Clone
git clone <repo-url> clove
cd clove

# Run install script
./scripts/install.sh

# Set up API key
cp .env.example .env
# Edit .env and add GEMINI_API_KEY
```

## Manual Install

### 1. System Dependencies

```bash
sudo apt update
sudo apt install -y build-essential cmake pkg-config libssl-dev python3 python3-pip
```

### 2. vcpkg (C++ package manager)

```bash
git clone https://github.com/Microsoft/vcpkg.git ~/vcpkg
~/vcpkg/bootstrap-vcpkg.sh
export VCPKG_ROOT="$HOME/vcpkg"
```

### 3. Python Dependencies

```bash
# Create and activate virtual environment
python3 -m venv clove_env
source clove_env/bin/activate

# Install dependencies
pip install google-genai websockets
```

### 4. Build Kernel

```bash
cd clove
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

### 5. Configure

```bash
cp .env.example .env
# Add your Gemini API key to .env
```

## Running Clove

### Start the Kernel

```bash
./build/clove_kernel
```

For full sandbox isolation (namespaces + cgroups):
```bash
sudo ./build/clove_kernel
```

### Run Your First Agent

```bash
python3 agents/examples/hello_agent.py
```

### Start the Metrics TUI

```bash
# Terminal 1: Kernel (already running)

# Terminal 2: Launch TUI
python3 agents/dashboard/metrics_tui.py
```

The TUI shows live system metrics (CPU, memory, disk, network) and active agents.
Press `q` to quit, `r` to force refresh.

### Start the Web Dashboard

```bash
# Terminal 1: Kernel (already running)

# Terminal 2: WebSocket proxy
python3 agents/dashboard/ws_proxy.py

# Terminal 3: HTTP server
cd agents/dashboard && python3 -m http.server 8000

# Open http://localhost:8000
```

## Basic SDK Usage

```python
from clove_sdk import CloveClient

with CloveClient() as client:
    # Echo test
    result = client.noop("Hello!")
    print(result)

    # LLM query
    response = client.think("What is 2+2?")
    print(response['content'])

    # Spawn an agent
    agent = client.spawn(
        name="worker",
        script="/path/to/agent.py",
        sandboxed=True
    )

    # List agents
    agents = client.list_agents()

    # Kill agent
    client.kill(name="worker")
```

## CLI Tool

The `clove` CLI provides fleet management and remote deployment.

### Install CLI

```bash
cd cli

# Make sure virtual environment is active
source ../clove_env/bin/activate

pip install -e .

# Or install dependencies manually
pip install -r requirements.txt
```

### Configure

```bash
# Set relay server URL
clove config set relay_url http://localhost:8766

# View configuration
clove config show
```

### Deploy to Docker

```bash
# Deploy a local Docker container
clove deploy docker --name dev-kernel

# Check status
clove status
```

### Deploy to AWS

```bash
# Deploy to AWS EC2
clove deploy aws --region us-east-1 --instance-type t3.micro

# View machines
clove machines list
```

### Deploy to GCP

```bash
# Deploy to GCP Compute Engine
clove deploy gcp --zone us-central1-a --machine-type n1-standard-1
```

### Run Agents Remotely

```bash
# Run on a specific machine
clove agent run agents/examples/hello_agent.py --machine docker-dev-kernel-abc123

# Run on all machines
clove agent run agents/examples/health_check.py --all

# List running agents
clove agent list
```

### Token Management

```bash
# Create machine token (for new kernels)
clove tokens create machine --name production-server

# Create agent token
clove tokens create agent --target-machine docker-dev-kernel-abc123

# List tokens
clove tokens list
```

## Fleet Management

### Start Relay Server

```bash
cd relay
pip install -r requirements.txt
python relay_server.py
```

The relay server runs on:
- WebSocket: `ws://localhost:8765` (kernel connections)
- REST API: `http://localhost:8766` (CLI management)

### Connect Kernel to Relay

```bash
# Using Python tunnel client
python scripts/tunnel_client.py --relay ws://relay.example.com:8765 --token <machine_token>
```

### Fleet Status

```bash
$ clove status

 Clove Fleet Status
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Machine ID            ┃ Provider   ┃ Status      ┃ Agents      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ docker-dev-abc123     │ docker     │ connected   │ 2           │
│ aws-i-0def456-us-e1   │ aws        │ connected   │ 0           │
└───────────────────────┴────────────┴─────────────┴─────────────┘
```

## Multi-Agent Benchmarks

Compare Clove against other frameworks like LangGraph:

```bash
# Install dependencies
pip install langgraph langchain-google-genai python-dotenv

# Run the benchmark
cd worlds/examples/research_team
python3 benchmark.py --iterations 3
```

This benchmark runs a 3-agent research team (Coordinator, Researcher, Writer) in three configurations:
- **LangGraph**: StateGraph pattern, single process
- **Clove Single-Process**: Kernel-mediated LLM calls
- **Clove Multi-Process**: Real process isolation with IPC messaging

See [worlds/examples/research_team/README.md](../worlds/examples/research_team/README.md) for details.

## Next Steps

- [Syscall Reference](syscalls.md) - All available syscalls
- [Architecture](architecture.md) - How Clove works
- [CLI Reference](../cli/README.md) - Full CLI documentation
- [Examples](../agents/examples/README.md) - Demo agents
- [Multi-Agent Benchmark](../worlds/examples/research_team/README.md) - Clove vs LangGraph comparison
