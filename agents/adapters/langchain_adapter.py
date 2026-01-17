"""
AgentOS LangChain Adapter

Exposes AgentOS syscalls as LangChain tools, enabling LangChain agents
to interact with the local system through AgentOS's permission system.

== Usage ==

```python
from langchain.agents import create_react_agent
from langchain_openai import ChatOpenAI
from agents.adapters.langchain_adapter import AgentOSToolkit

# Create toolkit connected to AgentOS
toolkit = AgentOSToolkit()
tools = toolkit.get_tools()

# Create LangChain agent with AgentOS tools
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
```

== Architecture ==

LangChain Agent
     |
     v
AgentOSToolkit (this adapter)
     |
     v
AgentOS Python SDK
     |
     v (Unix Socket IPC)
AgentOS Kernel
     |
     v
System Resources (files, processes, network)

All operations go through AgentOS's permission system.
"""

import os
import sys
from typing import Optional, Any, Type, List

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

# Try to import LangChain components
try:
    from langchain.tools import BaseTool
    from langchain.tools import StructuredTool
    from pydantic import BaseModel, Field
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Provide stub classes for when LangChain isn't installed
    class BaseTool:
        pass
    class BaseModel:
        pass
    def Field(*args, **kwargs):
        return None


# ============================================================================
# Input Schemas (Pydantic models for structured tool inputs)
# ============================================================================

if LANGCHAIN_AVAILABLE:
    class ReadInput(BaseModel):
        path: str = Field(description="Absolute path to the file to read")

    class WriteInput(BaseModel):
        path: str = Field(description="Absolute path to the file to write")
        content: str = Field(description="Content to write to the file")
        mode: str = Field(default="write", description="Write mode: 'write' or 'append'")

    class ExecInput(BaseModel):
        command: str = Field(description="Shell command to execute")
        cwd: Optional[str] = Field(default=None, description="Working directory")
        timeout: int = Field(default=30, description="Timeout in seconds")

    class ThinkInput(BaseModel):
        prompt: str = Field(description="Prompt to send to the LLM")
        system_instruction: Optional[str] = Field(default=None, description="System instruction")

    class SpawnInput(BaseModel):
        name: str = Field(description="Name for the agent")
        script: str = Field(description="Path to the Python script")
        sandboxed: bool = Field(default=True, description="Run in sandbox")

    class HTTPInput(BaseModel):
        url: str = Field(description="URL to request")
        method: str = Field(default="GET", description="HTTP method")
        headers: Optional[dict] = Field(default=None, description="Request headers")
        body: Optional[str] = Field(default=None, description="Request body")


# ============================================================================
# LangChain Tools
# ============================================================================

class AgentOSReadTool(BaseTool):
    """LangChain tool for reading files through AgentOS"""

    name: str = "agentos_read"
    description: str = "Read a file from the filesystem through AgentOS. Input should be an absolute file path."

    client: Optional[AgentOSClient] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, client: AgentOSClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    def _run(self, path: str) -> str:
        """Execute the tool"""
        result = self.client.read_file(path)
        if result.get("success"):
            return result.get("content", "")
        else:
            return f"Error: {result.get('error', 'Failed to read file')}"

    async def _arun(self, path: str) -> str:
        """Async version (falls back to sync)"""
        return self._run(path)


class AgentOSWriteTool(BaseTool):
    """LangChain tool for writing files through AgentOS"""

    name: str = "agentos_write"
    description: str = "Write content to a file through AgentOS. Provide path and content."

    client: Optional[AgentOSClient] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, client: AgentOSClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    def _run(self, path: str, content: str, mode: str = "write") -> str:
        """Execute the tool"""
        result = self.client.write_file(path, content, mode)
        if result.get("success"):
            return f"Successfully wrote {result.get('bytes_written', 0)} bytes to {path}"
        else:
            return f"Error: {result.get('error', 'Failed to write file')}"

    async def _arun(self, path: str, content: str, mode: str = "write") -> str:
        return self._run(path, content, mode)


class AgentOSExecTool(BaseTool):
    """LangChain tool for executing commands through AgentOS"""

    name: str = "agentos_exec"
    description: str = "Execute a shell command through AgentOS. Input should be the command string."

    client: Optional[AgentOSClient] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, client: AgentOSClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    def _run(self, command: str, cwd: Optional[str] = None, timeout: int = 30) -> str:
        """Execute the tool"""
        result = self.client.exec(command, cwd=cwd, timeout=timeout)
        output = []
        if result.get("stdout"):
            output.append(f"stdout:\n{result['stdout']}")
        if result.get("stderr"):
            output.append(f"stderr:\n{result['stderr']}")
        output.append(f"exit_code: {result.get('exit_code', -1)}")
        return "\n".join(output)

    async def _arun(self, command: str, cwd: Optional[str] = None, timeout: int = 30) -> str:
        return self._run(command, cwd, timeout)


class AgentOSThinkTool(BaseTool):
    """LangChain tool for querying LLM through AgentOS"""

    name: str = "agentos_think"
    description: str = "Query the LLM through AgentOS for reasoning tasks. Input should be the prompt."

    client: Optional[AgentOSClient] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, client: AgentOSClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    def _run(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Execute the tool"""
        result = self.client.think(prompt, system_instruction=system_instruction)
        if result.get("success"):
            return result.get("content", "")
        else:
            return f"Error: {result.get('error', 'LLM call failed')}"

    async def _arun(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        return self._run(prompt, system_instruction)


class AgentOSSpawnTool(BaseTool):
    """LangChain tool for spawning agents through AgentOS"""

    name: str = "agentos_spawn"
    description: str = "Spawn a new agent process through AgentOS. Provide agent name and script path."

    client: Optional[AgentOSClient] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, client: AgentOSClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    def _run(self, name: str, script: str, sandboxed: bool = True) -> str:
        """Execute the tool"""
        result = self.client.spawn(name=name, script=script, sandboxed=sandboxed)
        if result and result.get("status") == "running":
            return f"Spawned agent '{name}' with ID {result.get('id')} (PID: {result.get('pid')})"
        else:
            return f"Error: {result.get('error', 'Failed to spawn agent')}"

    async def _arun(self, name: str, script: str, sandboxed: bool = True) -> str:
        return self._run(name, script, sandboxed)


class AgentOSHTTPTool(BaseTool):
    """LangChain tool for making HTTP requests through AgentOS"""

    name: str = "agentos_http"
    description: str = "Make an HTTP request through AgentOS. Provide URL and optionally method, headers, body."

    client: Optional[AgentOSClient] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, client: AgentOSClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    def _run(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        body: Optional[str] = None
    ) -> str:
        """Execute the tool"""
        result = self.client.http(url=url, method=method, headers=headers, body=body)
        if result.get("success"):
            return f"Status: {result.get('status_code')}\n\n{result.get('body', '')}"
        else:
            return f"Error: {result.get('error', 'HTTP request failed')}"

    async def _arun(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        body: Optional[str] = None
    ) -> str:
        return self._run(url, method, headers, body)


# ============================================================================
# Toolkit (Collection of all tools)
# ============================================================================

class AgentOSToolkit:
    """
    LangChain toolkit providing all AgentOS tools.

    Usage:
        toolkit = AgentOSToolkit()
        tools = toolkit.get_tools()

        # Use with LangChain agent
        agent = create_react_agent(llm, tools, prompt)
    """

    def __init__(self, permission_level: str = "standard"):
        """
        Initialize the toolkit.

        Args:
            permission_level: AgentOS permission level (unrestricted, standard, sandboxed, readonly, minimal)
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is not installed. Install with: pip install langchain langchain-core pydantic"
            )

        self.client = AgentOSClient()
        if not self.client.connect():
            raise ConnectionError("Failed to connect to AgentOS kernel")

        self.client.set_permissions(level=permission_level)
        self.permission_level = permission_level

    def get_tools(self) -> List[BaseTool]:
        """Get all available AgentOS tools as LangChain tools"""
        return [
            AgentOSReadTool(client=self.client),
            AgentOSWriteTool(client=self.client),
            AgentOSExecTool(client=self.client),
            AgentOSThinkTool(client=self.client),
            AgentOSSpawnTool(client=self.client),
            AgentOSHTTPTool(client=self.client),
        ]

    def get_read_tools(self) -> List[BaseTool]:
        """Get only read-related tools (for readonly permission level)"""
        return [
            AgentOSReadTool(client=self.client),
        ]

    def get_execution_tools(self) -> List[BaseTool]:
        """Get tools that can execute code"""
        return [
            AgentOSExecTool(client=self.client),
            AgentOSSpawnTool(client=self.client),
        ]

    def disconnect(self):
        """Disconnect from AgentOS"""
        if self.client:
            self.client.disconnect()


# ============================================================================
# Convenience Functions
# ============================================================================

def create_agentos_tools(permission_level: str = "standard") -> List[BaseTool]:
    """
    Create AgentOS tools for LangChain.

    Convenience function that creates a toolkit and returns tools.

    Args:
        permission_level: AgentOS permission level

    Returns:
        List of LangChain tools
    """
    toolkit = AgentOSToolkit(permission_level=permission_level)
    return toolkit.get_tools()
