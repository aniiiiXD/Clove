# AgentOS MCP Server

This MCP (Model Context Protocol) server exposes AgentOS syscalls as tools for Claude Desktop.

## What This Enables

Claude Desktop can:
- Read and write files on your PC
- Execute shell commands
- Spawn and manage agents
- Query the LLM through AgentOS
- Make HTTP requests

All operations go through AgentOS's permission system.

## Installation

### 1. Make sure AgentOS kernel is running

```bash
cd /home/anixd/Documents/AGENTOS/build
./agentos_kernel
```

### 2. Add to Claude Desktop config

Edit `~/.config/Claude/claude_desktop_config.json` (Linux) or the equivalent on your OS:

```json
{
  "mcpServers": {
    "agentos": {
      "command": "python3",
      "args": ["/home/anixd/Documents/AGENTOS/agents/mcp/mcp_server.py"]
    }
  }
}
```

### 3. Restart Claude Desktop

Claude will now have access to AgentOS tools.

## Available Tools

| Tool | Description |
|------|-------------|
| `agentos_read` | Read a file from the filesystem |
| `agentos_write` | Write content to a file |
| `agentos_exec` | Execute a shell command |
| `agentos_think` | Query the LLM |
| `agentos_spawn` | Spawn a new agent |
| `agentos_list_agents` | List running agents |
| `agentos_kill` | Kill an agent |
| `agentos_http` | Make an HTTP request |

## Example Usage in Claude Desktop

Once configured, you can ask Claude:

- "Read the file /home/user/project/main.py"
- "Run `git status` in the current directory"
- "Spawn an agent called 'worker' from worker.py"
- "List all running agents"
- "Make a GET request to https://api.github.com"

## Security

All operations go through AgentOS's permission system:
- Path restrictions for file access
- Command filtering for exec
- Domain whitelist for HTTP
- Resource quotas for LLM

## Troubleshooting

### "Failed to connect to AgentOS kernel"

Make sure the kernel is running:
```bash
./build/agentos_kernel
```

### Tool not working

Check stderr output from the MCP server for error messages.

### Permission denied

The MCP server runs with "standard" permissions by default.
Modify the server to use "unrestricted" if needed (not recommended for untrusted use).
