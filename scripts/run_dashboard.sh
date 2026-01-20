#!/bin/bash
# Start AgentOS Dashboard (all components)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Starting AgentOS Dashboard..."
echo

# Check if kernel socket exists
if [ ! -S /tmp/agentos.sock ]; then
    echo "Warning: Kernel socket not found. Start kernel first:"
    echo "  ./scripts/run_kernel.sh"
    echo
fi

# Start WebSocket proxy in background
echo "[1/2] Starting WebSocket proxy..."
python3 agents/dashboard/ws_proxy.py &
WS_PID=$!

# Give it a moment to start
sleep 1

# Start HTTP server
echo "[2/2] Starting HTTP server on port 8000..."
echo
echo "Dashboard: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo

cd agents/dashboard
python3 -m http.server 8000

# Cleanup on exit
kill $WS_PID 2>/dev/null
