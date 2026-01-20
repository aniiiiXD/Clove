#!/bin/bash
# Start AgentOS kernel

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if kernel exists
if [ ! -f build/agentos_kernel ]; then
    echo "Kernel not built. Run: ./scripts/install.sh"
    exit 1
fi

# Run with or without sudo
if [ "$1" == "--sandbox" ] || [ "$1" == "-s" ]; then
    echo "Starting kernel with full sandbox (requires root)..."
    sudo ./build/agentos_kernel
else
    echo "Starting kernel..."
    ./build/agentos_kernel
fi
