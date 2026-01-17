#!/usr/bin/env python3
"""
AgentOS MCP Server

This implements a Model Context Protocol (MCP) server that exposes
AgentOS syscalls as tools for Claude Desktop and other MCP clients.

== What This Enables ==

Claude Desktop can:
- Spawn agents on your PC
- Access files (with permission)
- Run commands (with approval)
- Make HTTP requests
- All through the safe AgentOS layer

== MCP Protocol ==

MCP uses JSON-RPC 2.0 over stdio:
- Server reads JSON-RPC requests from stdin
- Server writes JSON-RPC responses to stdout

== Installation ==

Add to Claude Desktop config (claude_desktop_config.json):

{
  "mcpServers": {
    "agentos": {
      "command": "python3",
      "args": ["/path/to/mcp_server.py"]
    }
  }
}

== Usage ==

Once configured, Claude Desktop will have access to AgentOS tools:
- agentos_read: Read files
- agentos_write: Write files
- agentos_exec: Execute commands
- agentos_think: Query LLM
- agentos_spawn: Spawn agents
- agentos_http: Make HTTP requests

"""

import sys
import os
import json
import logging
from typing import Any, Optional

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

# Configure logging to stderr (stdout is for MCP protocol)
logging.basicConfig(
    level=logging.DEBUG,
    format='[MCP] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# MCP Protocol version
MCP_VERSION = "2024-11-05"

# AgentOS client (global for this server)
client: Optional[AgentOSClient] = None


def get_client() -> AgentOSClient:
    """Get or create the AgentOS client"""
    global client
    if client is None or client._sock is None:
        client = AgentOSClient()
        if not client.connect():
            raise ConnectionError("Failed to connect to AgentOS kernel")
        # Set unrestricted permissions for MCP (user trusts Claude Desktop)
        client.set_permissions(level="standard")
        logger.info("Connected to AgentOS kernel")
    return client


# ============================================================================
# Tool Definitions
# ============================================================================

TOOLS = [
    {
        "name": "agentos_read",
        "description": "Read a file from the local filesystem through AgentOS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "agentos_write",
        "description": "Write content to a file through AgentOS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "mode": {
                    "type": "string",
                    "enum": ["write", "append"],
                    "description": "Write mode: 'write' (overwrite) or 'append'",
                    "default": "write"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "agentos_exec",
        "description": "Execute a shell command through AgentOS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30)",
                    "default": 30
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "agentos_think",
        "description": "Query the LLM through AgentOS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt to send to the LLM"
                },
                "system_instruction": {
                    "type": "string",
                    "description": "Optional system instruction"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "agentos_spawn",
        "description": "Spawn a new agent process through AgentOS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the agent"
                },
                "script": {
                    "type": "string",
                    "description": "Path to the Python script to run"
                },
                "sandboxed": {
                    "type": "boolean",
                    "description": "Whether to run in sandbox (default: true)",
                    "default": True
                }
            },
            "required": ["name", "script"]
        }
    },
    {
        "name": "agentos_list_agents",
        "description": "List all running agents",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "agentos_kill",
        "description": "Kill a running agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the agent to kill"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "agentos_http",
        "description": "Make an HTTP request through AgentOS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to request"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP method",
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "Optional request headers"
                },
                "body": {
                    "type": "string",
                    "description": "Optional request body"
                }
            },
            "required": ["url"]
        }
    }
]


# ============================================================================
# Tool Handlers
# ============================================================================

def handle_tool_call(name: str, arguments: dict) -> dict:
    """Handle a tool call and return the result"""
    try:
        c = get_client()

        if name == "agentos_read":
            result = c.read_file(arguments["path"])
            if result.get("success"):
                return {"content": result.get("content", ""), "size": result.get("size", 0)}
            else:
                return {"error": result.get("error", "Failed to read file")}

        elif name == "agentos_write":
            result = c.write_file(
                arguments["path"],
                arguments["content"],
                arguments.get("mode", "write")
            )
            if result.get("success"):
                return {"bytes_written": result.get("bytes_written", 0)}
            else:
                return {"error": result.get("error", "Failed to write file")}

        elif name == "agentos_exec":
            result = c.exec(
                arguments["command"],
                cwd=arguments.get("cwd"),
                timeout=arguments.get("timeout", 30)
            )
            return {
                "success": result.get("success", False),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "exit_code": result.get("exit_code", -1)
            }

        elif name == "agentos_think":
            result = c.think(
                arguments["prompt"],
                system_instruction=arguments.get("system_instruction")
            )
            if result.get("success"):
                return {"content": result.get("content", ""), "tokens": result.get("tokens", 0)}
            else:
                return {"error": result.get("error", "LLM call failed")}

        elif name == "agentos_spawn":
            result = c.spawn(
                name=arguments["name"],
                script=arguments["script"],
                sandboxed=arguments.get("sandboxed", True)
            )
            if result and result.get("status") == "running":
                return {"id": result.get("id"), "pid": result.get("pid"), "status": "running"}
            else:
                return {"error": result.get("error", "Failed to spawn agent")}

        elif name == "agentos_list_agents":
            agents = c.list_agents()
            return {"agents": agents}

        elif name == "agentos_kill":
            killed = c.kill(name=arguments["name"])
            return {"killed": killed}

        elif name == "agentos_http":
            result = c.http(
                url=arguments["url"],
                method=arguments.get("method", "GET"),
                headers=arguments.get("headers"),
                body=arguments.get("body")
            )
            return result

        else:
            return {"error": f"Unknown tool: {name}"}

    except ConnectionError as e:
        return {"error": f"Not connected to AgentOS kernel: {e}"}
    except Exception as e:
        logger.exception(f"Tool call error: {e}")
        return {"error": str(e)}


# ============================================================================
# MCP Protocol Handler
# ============================================================================

def send_response(response: dict):
    """Send a JSON-RPC response to stdout"""
    json_str = json.dumps(response)
    sys.stdout.write(json_str + "\n")
    sys.stdout.flush()


def handle_request(request: dict) -> dict:
    """Handle a JSON-RPC request and return a response"""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    logger.debug(f"Received: {method}")

    # Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "agentos-mcp",
                    "version": "0.1.0"
                }
            }
        }

    # List tools
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }

    # Call tool
    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        result = handle_tool_call(tool_name, tool_args)

        # Format as MCP content
        content = []
        if "error" in result:
            content.append({
                "type": "text",
                "text": f"Error: {result['error']}"
            })
        else:
            content.append({
                "type": "text",
                "text": json.dumps(result, indent=2)
            })

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": content,
                "isError": "error" in result
            }
        }

    # Notifications (no response needed)
    elif method == "notifications/initialized":
        logger.info("MCP client initialized")
        return None

    # Unknown method
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def main():
    """Main MCP server loop"""
    logger.info("AgentOS MCP Server starting...")
    logger.info("Reading from stdin, writing to stdout")

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = handle_request(request)

                if response is not None:
                    send_response(response)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                send_response({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                })

    except KeyboardInterrupt:
        logger.info("Shutting down...")

    finally:
        if client and client._sock:
            client.disconnect()
            logger.info("Disconnected from AgentOS")


if __name__ == "__main__":
    main()
