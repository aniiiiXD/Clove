# AgentOS Dashboard - Quick Start Guide

## What You Get

A real-time web dashboard to monitor AgentOS agents with:
- Live agent status updates
- LLM token usage tracking
- Parent-child agent relationships
- Memory usage from cgroups
- Agent spawn/kill from browser

## 3-Step Setup

### Step 1: Start the Kernel

```bash
cd /home/anixd/Documents/AGENTOS
./build/agentos_kernel
```

You should see:
```
[INFO] AgentOS Kernel starting...
[INFO] Listening on /tmp/agentos.sock
```

### Step 2: Start the WebSocket Proxy

Open a new terminal:

```bash
cd /home/anixd/Documents/AGENTOS/agents/dashboard
python3 ws_proxy.py
```

You should see:
```
============================================================
AgentOS Dashboard WebSocket Proxy
============================================================
✓ Kernel connection verified
✓ WebSocket server listening on ws://localhost:8765
```

### Step 3: Open the Dashboard

Open a new terminal:

```bash
cd /home/anixd/Documents/AGENTOS/agents/dashboard
python3 -m http.server 8000
```

Then open your browser to: **http://localhost:8000**

## Testing It Out

### Test 1: Spawn an Agent from the Dashboard

1. Click "**+ Spawn Agent**"
2. Name: `hello-agent`
3. Script: `/home/anixd/Documents/AGENTOS/agents/examples/hello_agent.py`
4. Click "**Spawn**"

Watch the dashboard update in real-time!

### Test 2: Run a Demo

In a new terminal:

```bash
cd /home/anixd/Documents/AGENTOS
python3 agents/examples/fault_isolation_demo.py
```

Watch the dashboard as multiple agents spawn, run, and terminate!

### Test 3: LLM Token Tracking

```bash
python3 agents/examples/thinking_agent.py
```

Interact with the LLM and watch token counts increase in the dashboard.

## Features Implemented

### C++ Kernel Enhancements
- ✅ `AgentMetrics` struct with comprehensive metrics
- ✅ LLM token usage tracking per agent
- ✅ Parent-child relationship tracking
- ✅ Memory usage from cgroups
- ✅ Uptime calculation

### Dashboard Features
- ✅ Real-time updates (1 second refresh)
- ✅ Agent cards with PID, status, state
- ✅ System statistics (total, running, stopped, failed)
- ✅ Agent hierarchy tree view
- ✅ Spawn agents from UI
- ✅ Kill agents from UI
- ✅ Auto-reconnect on disconnect
- ✅ Toast notifications
- ✅ Dark terminal theme

## Dashboard UI Overview

```
┌─────────────────────────────────────────────────┐
│ ⚙ AgentOS Dashboard        [Status: Connected] │
├─────────────────────────────────────────────────┤
│                                                 │
│  [0]  [0]  [0]  [0]                             │
│ Total Run  Stop Fail                            │
│                                                 │
│ ┌─────────────────┐  ┌─────────────────────┐   │
│ │ 🤖 Agents       │  │ 📊 System Overview  │   │
│ │                 │  │                     │   │
│ │ + Spawn Agent   │  │ WebSocket: ws://... │   │
│ │                 │  │ Last Update: ...    │   │
│ │ (agent cards)   │  │                     │   │
│ └─────────────────┘  └─────────────────────┘   │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ 🌳 Agent Hierarchy                          │ │
│ │                                             │ │
│ │ ● agent-1 (PID: 123) [RUNNING]             │ │
│ │   ├─ child-1 (PID: 124) [RUNNING]          │ │
│ │   └─ child-2 (PID: 125) [STOPPED]          │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Troubleshooting

### "Disconnected" in Dashboard

**Fix**: Make sure kernel and proxy are running:
```bash
# Terminal 1
./build/agentos_kernel

# Terminal 2
python3 agents/dashboard/ws_proxy.py
```

### "websockets module not found"

**Fix**:
```bash
pip install websockets
```

### Dashboard Shows No Agents

**Fix**: Spawn an agent or run an example:
```bash
python3 agents/examples/hello_agent.py /tmp/agentos.sock
```

## What Metrics Are Tracked

### Per Agent:
- **ID**: Unique agent identifier
- **Name**: Agent name
- **PID**: Process ID
- **State**: CREATED, STARTING, RUNNING, STOPPING, STOPPED, FAILED
- **Uptime**: Seconds since creation
- **Memory**: Bytes used (from cgroups)
- **LLM Requests**: Total LLM API calls
- **LLM Tokens**: Total tokens consumed
- **Parent ID**: ID of parent agent (0 = kernel)
- **Child IDs**: List of spawned child agents

### System-Wide:
- Total agents
- Running agents
- Stopped agents
- Failed agents

## Files Modified

### C++ Kernel:
1. `src/runtime/agent_process.hpp` - Added `AgentMetrics` struct and tracking fields
2. `src/runtime/agent_process.cpp` - Implemented metrics collection methods
3. `src/kernel/kernel.cpp` - Added LLM and parent-child tracking

### Dashboard:
1. `agents/dashboard/ws_proxy.py` - WebSocket bridge
2. `agents/dashboard/index.html` - Web UI
3. `agents/dashboard/README.md` - Full documentation

## Next Steps

### Enhancements You Could Add:
- [ ] CPU percentage calculation (requires time-series tracking)
- [ ] Historical metrics charts
- [ ] Log streaming to dashboard
- [ ] Search/filter agents
- [ ] Export metrics to CSV
- [ ] Custom alerts/notifications

### Try These:
1. Spawn multiple agents and watch the hierarchy
2. Test with LLM-heavy workloads to see token tracking
3. Monitor resource usage during stress tests
4. Use spawn/kill from UI instead of CLI

Enjoy your AgentOS monitoring dashboard! 🚀
