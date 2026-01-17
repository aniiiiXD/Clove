"""
AgentOS AutoGen Adapter

Enables Microsoft AutoGen agents to use AgentOS as their execution backend,
with all operations going through AgentOS's permission system.

== Usage ==

```python
from agents.adapters.autogen_adapter import AgentOSAssistant, AgentOSUserProxy

# Create an assistant with AgentOS tools
assistant = AgentOSAssistant(
    name="coder",
    llm_config={"config_list": [{"model": "gpt-4"}]}
)

# Create a user proxy that can execute through AgentOS
user_proxy = AgentOSUserProxy(
    name="user",
    human_input_mode="NEVER"
)

# Start conversation
user_proxy.initiate_chat(
    assistant,
    message="Create a simple Python script that prints hello world"
)
```

== Architecture ==

AutoGen Agents
     |
     v
AgentOSAssistant / AgentOSUserProxy (this adapter)
     |
     v
AgentOS Python SDK
     |
     v (Unix Socket IPC)
AgentOS Kernel
"""

import os
import sys
from typing import Optional, Dict, Any, List, Union, Callable

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

# Try to import AutoGen components
try:
    from autogen import AssistantAgent, UserProxyAgent, ConversableAgent
    AUTOGEN_AVAILABLE = True
except ImportError:
    AUTOGEN_AVAILABLE = False
    # Provide stubs
    class AssistantAgent:
        pass
    class UserProxyAgent:
        pass
    class ConversableAgent:
        pass


# ============================================================================
# AgentOS Function Tools for AutoGen
# ============================================================================

def create_agentos_functions(client: AgentOSClient) -> Dict[str, Callable]:
    """
    Create function definitions for AutoGen agents.

    Returns a dictionary of functions that can be registered with AutoGen agents.
    """

    def read_file(path: str) -> str:
        """
        Read the contents of a file.

        Args:
            path: Absolute path to the file

        Returns:
            The file contents or an error message
        """
        result = client.read_file(path)
        if result.get("success"):
            return result.get("content", "")
        return f"Error: {result.get('error', 'Failed to read file')}"

    def write_file(path: str, content: str, mode: str = "write") -> str:
        """
        Write content to a file.

        Args:
            path: Absolute path to the file
            content: Content to write
            mode: 'write' (overwrite) or 'append'

        Returns:
            Success message or error
        """
        result = client.write_file(path, content, mode)
        if result.get("success"):
            return f"Successfully wrote {result.get('bytes_written', 0)} bytes to {path}"
        return f"Error: {result.get('error', 'Failed to write file')}"

    def execute_command(command: str, cwd: Optional[str] = None, timeout: int = 30) -> str:
        """
        Execute a shell command.

        Args:
            command: The command to execute
            cwd: Optional working directory
            timeout: Timeout in seconds

        Returns:
            Command output (stdout, stderr, exit code)
        """
        result = client.exec(command, cwd=cwd, timeout=timeout)
        output = []
        if result.get("stdout"):
            output.append(f"stdout:\n{result['stdout']}")
        if result.get("stderr"):
            output.append(f"stderr:\n{result['stderr']}")
        output.append(f"exit_code: {result.get('exit_code', -1)}")
        return "\n".join(output)

    def think(prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Query the LLM through AgentOS.

        Args:
            prompt: The prompt to send
            system_instruction: Optional system instruction

        Returns:
            LLM response or error
        """
        result = client.think(prompt, system_instruction=system_instruction)
        if result.get("success"):
            return result.get("content", "")
        return f"Error: {result.get('error', 'LLM call failed')}"

    def http_request(url: str, method: str = "GET", headers: Optional[Dict] = None, body: Optional[str] = None) -> str:
        """
        Make an HTTP request.

        Args:
            url: The URL to request
            method: HTTP method (GET, POST, etc.)
            headers: Optional request headers
            body: Optional request body

        Returns:
            Response status and body
        """
        result = client.http(url=url, method=method, headers=headers, body=body)
        if result.get("success"):
            status = result.get("status_code", "unknown")
            response_body = result.get("body", "")
            if len(response_body) > 5000:
                response_body = response_body[:5000] + "\n... [truncated]"
            return f"Status: {status}\n\n{response_body}"
        return f"Error: {result.get('error', 'HTTP request failed')}"

    def spawn_agent(name: str, script: str, sandboxed: bool = True) -> str:
        """
        Spawn a new agent process.

        Args:
            name: Name for the agent
            script: Path to the Python script
            sandboxed: Whether to run in sandbox

        Returns:
            Agent info or error
        """
        result = client.spawn(name=name, script=script, sandboxed=sandboxed)
        if result and result.get("status") == "running":
            return f"Spawned agent '{name}' with ID {result.get('id')} (PID: {result.get('pid')})"
        return f"Error: {result.get('error', 'Failed to spawn agent')}"

    def list_agents() -> str:
        """
        List all running agents.

        Returns:
            List of running agents
        """
        agents = client.list_agents()
        if not agents:
            return "No agents currently running"

        lines = ["Running agents:"]
        for agent in agents:
            lines.append(f"  - {agent.get('name', 'unknown')} (ID: {agent.get('id')}, Status: {agent.get('status')})")
        return "\n".join(lines)

    def kill_agent(name: str) -> str:
        """
        Kill a running agent.

        Args:
            name: Name of the agent to kill

        Returns:
            Success or error message
        """
        killed = client.kill(name=name)
        if killed:
            return f"Successfully killed agent '{name}'"
        return f"Failed to kill agent '{name}'"

    return {
        "read_file": read_file,
        "write_file": write_file,
        "execute_command": execute_command,
        "think": think,
        "http_request": http_request,
        "spawn_agent": spawn_agent,
        "list_agents": list_agents,
        "kill_agent": kill_agent,
    }


# ============================================================================
# Function Schemas for AutoGen
# ============================================================================

AGENTOS_FUNCTION_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the filesystem",
        "parameters": {
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
        "name": "write_file",
        "description": "Write content to a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                },
                "mode": {
                    "type": "string",
                    "enum": ["write", "append"],
                    "description": "Write mode"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "execute_command",
        "description": "Execute a shell command",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute"
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "think",
        "description": "Query the LLM for reasoning tasks",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt to send"
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
        "name": "http_request",
        "description": "Make an HTTP request",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to request"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP method"
                },
                "headers": {
                    "type": "object",
                    "description": "Request headers"
                },
                "body": {
                    "type": "string",
                    "description": "Request body"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "spawn_agent",
        "description": "Spawn a new agent process",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the agent"
                },
                "script": {
                    "type": "string",
                    "description": "Path to the Python script"
                },
                "sandboxed": {
                    "type": "boolean",
                    "description": "Run in sandbox"
                }
            },
            "required": ["name", "script"]
        }
    },
    {
        "name": "list_agents",
        "description": "List all running agents",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "kill_agent",
        "description": "Kill a running agent",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the agent to kill"
                }
            },
            "required": ["name"]
        }
    }
]


# ============================================================================
# AutoGen Agent Classes
# ============================================================================

class AgentOSAssistant(AssistantAgent if AUTOGEN_AVAILABLE else object):
    """
    An AutoGen AssistantAgent with AgentOS tools registered.

    This assistant can use AgentOS functions to interact with the system.
    """

    def __init__(
        self,
        name: str,
        llm_config: Optional[Dict] = None,
        permission_level: str = "standard",
        system_message: Optional[str] = None,
        **kwargs
    ):
        """
        Create an AgentOS-enabled assistant.

        Args:
            name: Agent name
            llm_config: LLM configuration for AutoGen
            permission_level: AgentOS permission level
            system_message: Optional system message (default provides AgentOS context)
            **kwargs: Additional AutoGen arguments
        """
        if not AUTOGEN_AVAILABLE:
            raise ImportError("AutoGen is not installed. Install with: pip install pyautogen")

        # Connect to AgentOS
        self._agentos_client = AgentOSClient()
        if not self._agentos_client.connect():
            raise ConnectionError("Failed to connect to AgentOS kernel")
        self._agentos_client.set_permissions(level=permission_level)

        # Create function tools
        self._agentos_functions = create_agentos_functions(self._agentos_client)

        # Default system message
        if system_message is None:
            system_message = """You are an AI assistant with access to AgentOS tools.

Available tools:
- read_file: Read files from the filesystem
- write_file: Write content to files
- execute_command: Execute shell commands
- think: Query the LLM for reasoning
- http_request: Make HTTP requests
- spawn_agent: Spawn new agent processes
- list_agents: List running agents
- kill_agent: Kill an agent

Use these tools to complete tasks. All operations go through AgentOS's permission system."""

        # Configure function calling in llm_config
        if llm_config:
            llm_config = dict(llm_config)  # Copy to avoid modifying original
            llm_config["functions"] = AGENTOS_FUNCTION_SCHEMAS

        super().__init__(
            name=name,
            llm_config=llm_config,
            system_message=system_message,
            **kwargs
        )

    def get_agentos_client(self) -> AgentOSClient:
        """Get the underlying AgentOS client"""
        return self._agentos_client

    def disconnect(self):
        """Disconnect from AgentOS"""
        if self._agentos_client:
            self._agentos_client.disconnect()


class AgentOSUserProxy(UserProxyAgent if AUTOGEN_AVAILABLE else object):
    """
    An AutoGen UserProxyAgent that executes code through AgentOS.

    Instead of executing code directly, this proxy routes execution
    through AgentOS's permission system.
    """

    def __init__(
        self,
        name: str,
        permission_level: str = "standard",
        human_input_mode: str = "TERMINATE",
        max_consecutive_auto_reply: int = 10,
        code_execution_config: Optional[Dict] = None,
        **kwargs
    ):
        """
        Create an AgentOS-enabled user proxy.

        Args:
            name: Agent name
            permission_level: AgentOS permission level
            human_input_mode: When to ask for human input
            max_consecutive_auto_reply: Max auto replies
            code_execution_config: Code execution config (AgentOS handles execution)
            **kwargs: Additional AutoGen arguments
        """
        if not AUTOGEN_AVAILABLE:
            raise ImportError("AutoGen is not installed. Install with: pip install pyautogen")

        # Connect to AgentOS
        self._agentos_client = AgentOSClient()
        if not self._agentos_client.connect():
            raise ConnectionError("Failed to connect to AgentOS kernel")
        self._agentos_client.set_permissions(level=permission_level)

        # Create function tools
        self._agentos_functions = create_agentos_functions(self._agentos_client)

        # Configure code execution through AgentOS
        if code_execution_config is None:
            code_execution_config = {
                "work_dir": "/tmp/autogen_agentos",
                "use_docker": False,  # We use AgentOS sandboxing instead
            }

        super().__init__(
            name=name,
            human_input_mode=human_input_mode,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            code_execution_config=code_execution_config,
            function_map=self._agentos_functions,
            **kwargs
        )

    def execute_code_blocks(self, code_blocks: List) -> tuple:
        """
        Execute code blocks through AgentOS.

        Overrides the default execution to route through AgentOS.
        """
        results = []
        for lang, code in code_blocks:
            if lang.lower() in ["python", "py"]:
                # Write code to temp file and execute
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                    temp_path = f.name

                result = self._agentos_client.exec(f"python3 {temp_path}", timeout=60)
                output = result.get("stdout", "") + result.get("stderr", "")
                exit_code = result.get("exit_code", -1)

                # Cleanup
                self._agentos_client.exec(f"rm {temp_path}")

                results.append((exit_code, output))
            elif lang.lower() in ["bash", "sh", "shell"]:
                result = self._agentos_client.exec(code, timeout=60)
                output = result.get("stdout", "") + result.get("stderr", "")
                exit_code = result.get("exit_code", -1)
                results.append((exit_code, output))
            else:
                results.append((1, f"Unsupported language: {lang}"))

        # Combine results
        if results:
            exit_code = max(r[0] for r in results)
            output = "\n---\n".join(r[1] for r in results)
            return exit_code, output
        return 0, ""

    def get_agentos_client(self) -> AgentOSClient:
        """Get the underlying AgentOS client"""
        return self._agentos_client

    def disconnect(self):
        """Disconnect from AgentOS"""
        if self._agentos_client:
            self._agentos_client.disconnect()


# ============================================================================
# Convenience Functions
# ============================================================================

def create_agentos_group_chat(
    agents: List[str],
    permission_level: str = "standard",
    llm_config: Optional[Dict] = None
) -> tuple:
    """
    Create a group chat with AgentOS-enabled agents.

    Args:
        agents: List of agent names/roles to create
        permission_level: AgentOS permission level
        llm_config: LLM configuration

    Returns:
        Tuple of (agents_list, GroupChat, GroupChatManager)
    """
    if not AUTOGEN_AVAILABLE:
        raise ImportError("AutoGen is not installed")

    from autogen import GroupChat, GroupChatManager

    created_agents = []

    # Create user proxy
    user_proxy = AgentOSUserProxy(
        name="user_proxy",
        permission_level=permission_level,
        human_input_mode="TERMINATE",
    )
    created_agents.append(user_proxy)

    # Create assistants for each role
    for agent_name in agents:
        assistant = AgentOSAssistant(
            name=agent_name,
            llm_config=llm_config,
            permission_level=permission_level,
        )
        created_agents.append(assistant)

    # Create group chat
    group_chat = GroupChat(
        agents=created_agents,
        messages=[],
        max_round=50
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config
    )

    return created_agents, group_chat, manager
