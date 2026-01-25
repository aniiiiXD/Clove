# Browser Extension Plan

## Overview

Add browser automation capabilities to CLOVE using Playwright MCP, enabling agents to control browsers via natural language commands - similar to Claude Code but for web browsing.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        CLOVE Kernel                            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                 Browser Agent (agentic loop)             │ │
│  │                                                          │ │
│  │   User: "Go to Moodle, download OS lecture 5"           │ │
│  │                        ↓                                 │ │
│  │   ┌────────────────────────────────────────┐            │ │
│  │   │          LLM (Gemini/Claude)           │            │ │
│  │   │   Decides actions based on page state  │            │ │
│  │   └────────────────────────────────────────┘            │ │
│  │                        ↓                                 │ │
│  │   ┌────────────────────────────────────────┐            │ │
│  │   │            MCP Client                  │            │ │
│  │   │   Translates LLM decisions to MCP      │            │ │
│  │   │   tool calls (navigate, click, type)   │            │ │
│  │   └────────────────────────────────────────┘            │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                            ↓ stdio
                ┌─────────────────────────┐
                │  Playwright MCP Server  │
                │  (@playwright/mcp)      │
                └─────────────────────────┘
                            ↓
                ┌─────────────────────────┐
                │   Browser (Chromium)    │
                └─────────────────────────┘
```

---

## Components

### 1. MCP Client (`agents/python_sdk/mcp_client.py`)

Generic MCP client that can connect to any MCP server via stdio or SSE.

**Responsibilities:**
- Spawn and manage MCP server processes
- List available tools from server
- Execute tool calls and return results
- Handle connection lifecycle

**Interface:**
```python
class MCPClient:
    def __init__(self, server_command: list[str], server_args: list[str] = None):
        """Initialize MCP client with server command."""
        pass

    async def connect(self) -> None:
        """Start MCP server and establish connection."""
        pass

    async def list_tools(self) -> list[Tool]:
        """Get available tools from server."""
        pass

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Execute a tool and return result."""
        pass

    async def disconnect(self) -> None:
        """Shutdown MCP server connection."""
        pass
```

### 2. Browser Agent (`agents/browser_agent/agent.py`)

Agentic loop pre-configured with Playwright MCP tools for browser automation.

**Responsibilities:**
- Initialize Playwright MCP connection
- Register browser tools with agentic loop
- Handle SSO session persistence (cookies)
- Execute natural language browser commands

**Interface:**
```python
class BrowserAgent:
    def __init__(self, headless: bool = False, persist_session: bool = True):
        """Initialize browser agent."""
        pass

    async def start(self) -> None:
        """Start browser and MCP server."""
        pass

    async def run(self, task: str) -> str:
        """Execute a browser task via natural language."""
        pass

    async def save_session(self, path: str) -> None:
        """Save browser cookies/session for SSO persistence."""
        pass

    async def load_session(self, path: str) -> None:
        """Load previously saved session."""
        pass

    async def stop(self) -> None:
        """Close browser and cleanup."""
        pass
```

### 3. Session Manager (`agents/browser_agent/session.py`)

Handles SSO session persistence across browser restarts.

**Responsibilities:**
- Save cookies to encrypted file
- Load cookies on browser start
- Handle session expiry/refresh
- Support multiple site sessions

**Storage:**
```
~/.clove/browser_sessions/
├── moodle.university.edu.json
├── github.com.json
└── ...
```

---

## Playwright MCP Tools

The `@playwright/mcp` server exposes these tools:

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_click` | Click element by selector or text |
| `browser_type` | Type text into input field |
| `browser_snapshot` | Get page accessibility snapshot (for LLM) |
| `browser_screenshot` | Capture page screenshot |
| `browser_scroll` | Scroll page up/down |
| `browser_select` | Select dropdown option |
| `browser_hover` | Hover over element |
| `browser_back` | Go back in history |
| `browser_forward` | Go forward in history |
| `browser_reload` | Reload current page |

---

## File Structure

```
agents/
├── python_sdk/
│   ├── agentos.py              # Existing SDK
│   ├── agentic.py              # Existing agentic loop
│   └── mcp_client.py           # NEW: Generic MCP client
│
├── browser_agent/
│   ├── __init__.py
│   ├── agent.py                # NEW: Browser-capable agent
│   ├── session.py              # NEW: Session/cookie manager
│   ├── config.py               # NEW: Configuration
│   └── prompts.py              # NEW: System prompts for browser agent
│
└── examples/
    ├── moodle_agent.py         # NEW: Example Moodle automation
    └── browser_demo.py         # NEW: General browser demo
```

---

## Implementation Steps

### Phase 1: MCP Client
- [ ] Implement base MCP protocol (JSON-RPC over stdio)
- [ ] Add tool discovery (list_tools)
- [ ] Add tool execution (call_tool)
- [ ] Handle server lifecycle (spawn/kill)
- [ ] Add error handling and reconnection

### Phase 2: Browser Agent
- [ ] Create BrowserAgent class
- [ ] Integrate MCP client with Playwright MCP
- [ ] Wire tools into agentic loop
- [ ] Add browser-specific system prompt
- [ ] Test basic navigation flows

### Phase 3: Session Persistence
- [ ] Implement cookie extraction from browser
- [ ] Save/load cookies to disk
- [ ] Encrypt sensitive session data
- [ ] Handle session expiry detection
- [ ] Test SSO flows (login once, reuse session)

### Phase 4: Integration
- [ ] Add new syscall SYS_BROWSER (optional)
- [ ] Update CLI with browser commands
- [ ] Add to dashboard UI (browser preview panel)
- [ ] Write documentation
- [ ] Create example agents

---

## Usage Examples

### Basic Navigation
```python
from browser_agent import BrowserAgent

agent = BrowserAgent(headless=False)
await agent.start()

# Natural language command
result = await agent.run("Go to github.com and search for 'CLOVE agent OS'")

await agent.stop()
```

### Moodle with SSO
```python
from browser_agent import BrowserAgent

agent = BrowserAgent(persist_session=True)
await agent.start()

# First time: will prompt for SSO login
await agent.run("""
    Login to moodle.university.edu via SSO,
    then go to course 'Operating Systems',
    and download all PDF files from Week 5
""")

# Session saved automatically
await agent.stop()

# Next time: reuses session, no login needed
```

### As CLOVE Agent
```python
from clove_sdk import CloveOS

aos = CloveOS()
aos.register("browser_agent")

# Use via IPC from other agents
aos.send("browser_agent", {
    "task": "Check my Moodle notifications"
})
```

---

## Configuration

`agents/browser_agent/config.py`:
```python
BROWSER_CONFIG = {
    "headless": False,           # Show browser window
    "browser": "chromium",       # chromium, firefox, webkit
    "viewport": {
        "width": 1280,
        "height": 720
    },
    "timeout": 30000,            # Navigation timeout (ms)
    "session_dir": "~/.clove/browser_sessions",
    "allowed_domains": [         # Optional domain whitelist
        "moodle.university.edu",
        "github.com",
        "*"                      # Or allow all
    ]
}

MCP_CONFIG = {
    "server": "npx",
    "args": ["@playwright/mcp@latest"],
    "transport": "stdio"
}
```

---

## System Prompt for Browser Agent

```
You are a browser automation agent. You can control a web browser to complete tasks.

Available tools:
- browser_navigate(url): Go to a URL
- browser_click(selector): Click an element
- browser_type(selector, text): Type into an input
- browser_snapshot(): Get current page state
- browser_screenshot(): Capture screenshot

When given a task:
1. Use browser_snapshot() to understand current page
2. Decide the next action based on page state
3. Execute action (click, type, navigate)
4. Repeat until task is complete

For SSO/login flows:
- Navigate to login page
- Wait for user to complete authentication if needed
- Confirm login success before proceeding

Always verify actions succeeded by checking page state after each step.
```

---

## Dependencies

```
# Python
pip install mcp playwright

# Node (for Playwright MCP server)
npm install -g @playwright/mcp

# Playwright browsers
playwright install chromium
```

---

## Security Considerations

1. **Domain Restrictions**: Optionally limit which domains the agent can access
2. **Session Encryption**: Encrypt stored cookies/sessions at rest
3. **Credential Handling**: Never log or store passwords in plain text
4. **Sandbox Integration**: Run browser in CLOVE sandbox with restricted permissions
5. **User Confirmation**: Optionally require user confirmation for sensitive actions (payments, account changes)

---

## Future Enhancements

- [ ] Screenshot-based navigation (for sites with poor accessibility)
- [ ] Multi-tab support
- [ ] Download management (auto-organize downloaded files)
- [ ] Form auto-fill from secure storage
- [ ] Browser extension integration
- [ ] Record and replay workflows
- [ ] Integration with Claude Computer Use API
