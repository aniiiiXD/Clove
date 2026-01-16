# AgentOS Dashboard

Real-time web-based monitoring dashboard for AgentOS agents. Monitor agent status, resource usage, LLM activity, and process hierarchy from your browser.

## Features

- **Real-Time Monitoring**: Live updates every second via WebSocket
- **Agent Management**: Spawn and kill agents directly from the UI
- **Process Hierarchy**: Visualize parent-child relationships
- **System Statistics**: Total, running, stopped, and failed agent counts
- **Dark Theme**: Terminal-inspired aesthetic
- **Auto-Reconnect**: Automatically reconnects when kernel restarts

## Architecture

```
Browser (localhost:8000)
    ↕ WebSocket (ws://localhost:8765)
Python WebSocket Proxy (ws_proxy.py)
    ↕ Unix Socket (/tmp/agentos.sock)
AgentOS Kernel (agentos_kernel)
```

The dashboard uses a Python WebSocket proxy to bridge the browser to the kernel's Unix domain socket.

## Quick Start

### Prerequisites

```bash
# Install websockets library
pip install websockets
```

### Step 1: Start the AgentOS Kernel

```bash
cd /home/anixd/Documents/AGENTOS
./build/agentos_kernel
```

### Step 2: Start the WebSocket Proxy

In a new terminal:

```bash
cd /home/anixd/Documents/AGENTOS/agents/dashboard
python3 ws_proxy.py
```

You should see:
```
============================================================
AgentOS Dashboard WebSocket Proxy
============================================================
Kernel socket: /tmp/agentos.sock
WebSocket port: 8765

✓ Kernel connection verified
✓ WebSocket server listening on ws://localhost:8765
✓ Open dashboard: http://localhost:8000
```

### Step 3: Serve the Dashboard

In another terminal:

```bash
cd /home/anixd/Documents/AGENTOS/agents/dashboard
python3 -m http.server 8000
```

### Step 4: Open in Browser

Navigate to: **http://localhost:8000**

## Usage

### Viewing Agents

The dashboard automatically displays all running agents with:
- Agent name and ID
- Process ID (PID)
- Current state (RUNNING, STOPPED, FAILED, etc.)
- Real-time status updates

### Spawning an Agent

1. Click **"+ Spawn Agent"** button
2. Enter agent name (e.g., `worker-1`)
3. Enter script path (e.g., `/path/to/agents/examples/hello_agent.py`)
4. Toggle sandboxing if needed
5. Click **"Spawn"**

Example script paths:
- `agents/examples/hello_agent.py`
- `agents/examples/thinking_agent.py`
- `agents/examples/cpu_hog_agent.py`

### Killing an Agent

Click the **"Kill"** button on any agent card to terminate that agent.

### Viewing Hierarchy

The hierarchy tree shows parent-child relationships:
- **Root level**: Agents spawned directly by the kernel
- **Children**: Agents spawned by other agents (if parent_id tracking is implemented)

## Testing the Dashboard

### Test with Example Agents

```bash
# Terminal 1: Start kernel
./build/agentos_kernel

# Terminal 2: Start proxy
python3 agents/dashboard/ws_proxy.py

# Terminal 3: Serve dashboard
cd agents/dashboard && python3 -m http.server 8000

# Terminal 4: Run demo
python3 agents/examples/fault_isolation_demo.py
```

Watch the dashboard as agents spawn, run, and terminate!

### Test with Manual Spawning

From the dashboard UI, spawn an agent:
- Name: `test-agent`
- Script: `/home/anixd/Documents/AGENTOS/agents/examples/hello_agent.py`

You should see the agent appear in the list and can kill it with the button.

## Configuration

### WebSocket Proxy Options

```bash
python3 ws_proxy.py --help

Options:
  --socket PATH    Path to kernel socket (default: /tmp/agentos.sock)
  --port PORT      WebSocket port (default: 8765)
```

Example with custom settings:
```bash
python3 ws_proxy.py --socket /tmp/custom.sock --port 9000
```

Then update the WebSocket URL in `index.html` line 533:
```javascript
const wsUrl = 'ws://localhost:9000';
```

## Troubleshooting

### "Disconnected" Status

**Problem**: Dashboard shows "Disconnected" status

**Solutions**:
1. Ensure kernel is running: `./build/agentos_kernel`
2. Ensure proxy is running: `python3 ws_proxy.py`
3. Check kernel socket exists: `ls -la /tmp/agentos.sock`
4. Check proxy output for errors

### "websockets module not found"

**Problem**: `ModuleNotFoundError: No module named 'websockets'`

**Solution**:
```bash
pip install websockets
```

### Can't Connect to Dashboard

**Problem**: Browser can't load http://localhost:8000

**Solution**:
```bash
# Make sure HTTP server is running
cd agents/dashboard
python3 -m http.server 8000
```

### Agents Not Showing Up

**Problem**: Dashboard is connected but shows no agents

**Solutions**:
1. Check kernel has agents running: Run an example script
2. Check browser console for errors (F12 → Console tab)
3. Verify WebSocket connection in Network tab

## Development

### File Structure

```
agents/dashboard/
├── index.html       # Main dashboard (single-page app)
├── ws_proxy.py      # WebSocket proxy bridge
└── README.md        # This file
```

### Modifying the Dashboard

The dashboard is a single HTML file with embedded CSS and JavaScript. No build step required!

To make changes:
1. Edit `index.html`
2. Refresh browser (Ctrl+R or Cmd+R)

### Adding Features

**Example: Add a custom stat**

In `index.html`, add to the stats grid (around line 445):
```html
<div class="stat-card">
    <div class="stat-value" id="stat-custom">0</div>
    <div class="stat-label">Custom Metric</div>
</div>
```

Then update in JavaScript (around line 536):
```javascript
document.getElementById('stat-custom').textContent = myValue;
```

## WebSocket Protocol

### Client → Server

```json
{
  "type": "list_agents"
}

{
  "type": "spawn_agent",
  "payload": {
    "name": "worker-1",
    "script": "/path/to/script.py",
    "sandboxed": true
  }
}

{
  "type": "kill_agent",
  "name": "worker-1"
}
```

### Server → Client

```json
{
  "type": "agent_list",
  "data": [
    {
      "id": 1,
      "name": "worker-1",
      "pid": 12345,
      "state": "RUNNING",
      "running": true
    }
  ]
}

{
  "type": "metrics_update",
  "timestamp": 1705486425000,
  "agents": [...]
}
```

## Future Enhancements

Planned features:
- [ ] LLM token usage tracking
- [ ] CPU and memory usage graphs
- [ ] Log streaming in dashboard
- [ ] Historical metrics charts
- [ ] Search and filter agents
- [ ] Export metrics to CSV
- [ ] Alert notifications
- [ ] Dark/light theme toggle

## License

Part of AgentOS - A microkernel for AI agents.

## Support

For issues or questions:
- Check the main AgentOS README
- Review the STATUS.md file
- Examine kernel logs for errors
