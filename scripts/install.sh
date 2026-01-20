#!/bin/bash
# AgentOS Installation Script

set -e

echo "================================"
echo "   AgentOS Installation"
echo "================================"
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Check OS
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}Error: AgentOS requires Linux${NC}"
    exit 1
fi

echo "[1/5] Installing system dependencies..."
if command -v apt &> /dev/null; then
    sudo apt update
    sudo apt install -y build-essential cmake pkg-config libssl-dev python3 python3-pip
elif command -v dnf &> /dev/null; then
    sudo dnf install -y gcc-c++ cmake openssl-devel python3 python3-pip
else
    echo -e "${RED}Unsupported package manager. Install manually: gcc, cmake, openssl-dev, python3${NC}"
    exit 1
fi
echo -e "${GREEN}✓ System dependencies installed${NC}"

echo
echo "[2/5] Setting up vcpkg..."
if [ -z "$VCPKG_ROOT" ]; then
    if [ ! -d "$HOME/vcpkg" ]; then
        git clone https://github.com/Microsoft/vcpkg.git ~/vcpkg
        ~/vcpkg/bootstrap-vcpkg.sh
    fi
    export VCPKG_ROOT="$HOME/vcpkg"
    echo "export VCPKG_ROOT=\"\$HOME/vcpkg\"" >> ~/.bashrc
fi
echo -e "${GREEN}✓ vcpkg ready at $VCPKG_ROOT${NC}"

echo
echo "[3/5] Installing Python dependencies..."
pip3 install --user google-genai websockets
echo -e "${GREEN}✓ Python dependencies installed${NC}"

echo
echo "[4/5] Building kernel..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

mkdir -p build
cd build
cmake ..
make -j$(nproc)
echo -e "${GREEN}✓ Kernel built successfully${NC}"

echo
echo "[5/5] Setting up configuration..."
cd "$PROJECT_DIR"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${RED}⚠ Created .env file - add your GEMINI_API_KEY${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

echo
echo "================================"
echo -e "${GREEN}   Installation Complete!${NC}"
echo "================================"
echo
echo "Next steps:"
echo "  1. Add your API key: nano .env"
echo "  2. Start the kernel: ./build/agentos_kernel"
echo "  3. Run an example:   python3 agents/examples/hello_agent.py"
echo
