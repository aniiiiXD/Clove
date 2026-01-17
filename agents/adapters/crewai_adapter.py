"""
AgentOS CrewAI Adapter

Enables CrewAI agents to use AgentOS as their execution backend,
with all operations going through AgentOS's permission system.

== Usage ==

```python
from crewai import Agent, Task, Crew
from agents.adapters.crewai_adapter import AgentOSCrewAgent, AgentOSCrewTools

# Create tools from AgentOS
tools = AgentOSCrewTools()

# Create a CrewAI agent with AgentOS tools
researcher = Agent(
    role="Researcher",
    goal="Find information about a topic",
    backstory="You are a skilled researcher",
    tools=tools.get_tools(),
    allow_delegation=False
)

# Create tasks and crew as normal
task = Task(
    description="Research the latest AI trends",
    agent=researcher
)
crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()
```

== Architecture ==

CrewAI Agent
     |
     v
AgentOSCrewTools (this adapter)
     |
     v
AgentOS Python SDK
     |
     v (Unix Socket IPC)
AgentOS Kernel
"""

import os
import sys
from typing import Optional, Any, List, Callable

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from agentos import AgentOSClient

# Try to import CrewAI components
try:
    from crewai import Agent
    from crewai.tools import BaseTool as CrewBaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    # Provide stubs
    class CrewBaseTool:
        pass
    class Agent:
        pass


# ============================================================================
# CrewAI Tools
# ============================================================================

class AgentOSReadFileTool(CrewBaseTool if CREWAI_AVAILABLE else object):
    """CrewAI tool for reading files through AgentOS"""

    name: str = "Read File"
    description: str = "Read the contents of a file from the filesystem. Input: absolute file path."

    def __init__(self, client: AgentOSClient):
        super().__init__()
        self._client = client

    def _run(self, path: str) -> str:
        result = self._client.read_file(path)
        if result.get("success"):
            return result.get("content", "")
        return f"Error: {result.get('error', 'Failed to read file')}"


class AgentOSWriteFileTool(CrewBaseTool if CREWAI_AVAILABLE else object):
    """CrewAI tool for writing files through AgentOS"""

    name: str = "Write File"
    description: str = "Write content to a file. Input format: 'path|||content' (use ||| as separator)."

    def __init__(self, client: AgentOSClient):
        super().__init__()
        self._client = client

    def _run(self, input_str: str) -> str:
        # Parse input (path|||content format)
        if "|||" not in input_str:
            return "Error: Input must be in format 'path|||content'"

        parts = input_str.split("|||", 1)
        path = parts[0].strip()
        content = parts[1]

        result = self._client.write_file(path, content)
        if result.get("success"):
            return f"Successfully wrote {result.get('bytes_written', 0)} bytes to {path}"
        return f"Error: {result.get('error', 'Failed to write file')}"


class AgentOSExecuteCommandTool(CrewBaseTool if CREWAI_AVAILABLE else object):
    """CrewAI tool for executing shell commands through AgentOS"""

    name: str = "Execute Command"
    description: str = "Execute a shell command and return the output. Input: the command to run."

    def __init__(self, client: AgentOSClient):
        super().__init__()
        self._client = client

    def _run(self, command: str) -> str:
        result = self._client.exec(command, timeout=30)
        output = []
        if result.get("stdout"):
            output.append(result["stdout"])
        if result.get("stderr"):
            output.append(f"[stderr] {result['stderr']}")
        if not output:
            output.append(f"Command completed with exit code {result.get('exit_code', -1)}")
        return "\n".join(output)


class AgentOSThinkTool(CrewBaseTool if CREWAI_AVAILABLE else object):
    """CrewAI tool for querying LLM through AgentOS"""

    name: str = "Think"
    description: str = "Query an LLM for reasoning or analysis. Input: the prompt/question."

    def __init__(self, client: AgentOSClient):
        super().__init__()
        self._client = client

    def _run(self, prompt: str) -> str:
        result = self._client.think(prompt)
        if result.get("success"):
            return result.get("content", "")
        return f"Error: {result.get('error', 'LLM call failed')}"


class AgentOSHTTPRequestTool(CrewBaseTool if CREWAI_AVAILABLE else object):
    """CrewAI tool for making HTTP requests through AgentOS"""

    name: str = "HTTP Request"
    description: str = "Make an HTTP GET request. Input: the URL to fetch."

    def __init__(self, client: AgentOSClient):
        super().__init__()
        self._client = client

    def _run(self, url: str) -> str:
        result = self._client.http(url=url, method="GET")
        if result.get("success"):
            status = result.get("status_code", "unknown")
            body = result.get("body", "")
            # Truncate long responses
            if len(body) > 5000:
                body = body[:5000] + "\n... [truncated]"
            return f"Status: {status}\n\n{body}"
        return f"Error: {result.get('error', 'HTTP request failed')}"


class AgentOSSpawnAgentTool(CrewBaseTool if CREWAI_AVAILABLE else object):
    """CrewAI tool for spawning sub-agents through AgentOS"""

    name: str = "Spawn Agent"
    description: str = "Spawn a new agent process. Input format: 'name|||script_path'."

    def __init__(self, client: AgentOSClient):
        super().__init__()
        self._client = client

    def _run(self, input_str: str) -> str:
        if "|||" not in input_str:
            return "Error: Input must be in format 'name|||script_path'"

        parts = input_str.split("|||", 1)
        name = parts[0].strip()
        script = parts[1].strip()

        result = self._client.spawn(name=name, script=script, sandboxed=True)
        if result and result.get("status") == "running":
            return f"Spawned agent '{name}' with ID {result.get('id')}"
        return f"Error: {result.get('error', 'Failed to spawn agent')}"


class AgentOSListAgentsTool(CrewBaseTool if CREWAI_AVAILABLE else object):
    """CrewAI tool for listing running agents"""

    name: str = "List Agents"
    description: str = "List all running agents in AgentOS. Input: ignored (just call with empty string)."

    def __init__(self, client: AgentOSClient):
        super().__init__()
        self._client = client

    def _run(self, _: str = "") -> str:
        agents = self._client.list_agents()
        if not agents:
            return "No agents currently running"

        lines = ["Running agents:"]
        for agent in agents:
            lines.append(f"  - {agent.get('name', 'unknown')} (ID: {agent.get('id')}, Status: {agent.get('status')})")
        return "\n".join(lines)


# ============================================================================
# Tool Collection
# ============================================================================

class AgentOSCrewTools:
    """
    Collection of AgentOS tools for CrewAI.

    Usage:
        tools = AgentOSCrewTools()
        agent = Agent(
            role="Worker",
            goal="Complete tasks",
            tools=tools.get_tools()
        )
    """

    def __init__(self, permission_level: str = "standard"):
        """
        Initialize the tool collection.

        Args:
            permission_level: AgentOS permission level
        """
        if not CREWAI_AVAILABLE:
            raise ImportError(
                "CrewAI is not installed. Install with: pip install crewai"
            )

        self.client = AgentOSClient()
        if not self.client.connect():
            raise ConnectionError("Failed to connect to AgentOS kernel")

        self.client.set_permissions(level=permission_level)
        self.permission_level = permission_level

    def get_tools(self) -> list:
        """Get all available AgentOS tools"""
        return [
            AgentOSReadFileTool(self.client),
            AgentOSWriteFileTool(self.client),
            AgentOSExecuteCommandTool(self.client),
            AgentOSThinkTool(self.client),
            AgentOSHTTPRequestTool(self.client),
            AgentOSSpawnAgentTool(self.client),
            AgentOSListAgentsTool(self.client),
        ]

    def get_read_only_tools(self) -> list:
        """Get only read-related tools"""
        return [
            AgentOSReadFileTool(self.client),
            AgentOSHTTPRequestTool(self.client),
            AgentOSListAgentsTool(self.client),
        ]

    def get_file_tools(self) -> list:
        """Get file operation tools"""
        return [
            AgentOSReadFileTool(self.client),
            AgentOSWriteFileTool(self.client),
        ]

    def disconnect(self):
        """Disconnect from AgentOS"""
        if self.client:
            self.client.disconnect()


# ============================================================================
# Agent Factory
# ============================================================================

class AgentOSCrewAgent:
    """
    Factory for creating CrewAI agents backed by AgentOS.

    Usage:
        factory = AgentOSCrewAgent()

        researcher = factory.create(
            role="Researcher",
            goal="Find and analyze information",
            backstory="Expert at finding information online"
        )
    """

    def __init__(self, permission_level: str = "standard"):
        """
        Initialize the agent factory.

        Args:
            permission_level: AgentOS permission level for all created agents
        """
        self.tools = AgentOSCrewTools(permission_level=permission_level)

    def create(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: Optional[list] = None,
        allow_delegation: bool = False,
        verbose: bool = True,
        **kwargs
    ) -> Agent:
        """
        Create a CrewAI agent with AgentOS tools.

        Args:
            role: The agent's role
            goal: The agent's goal
            backstory: The agent's backstory
            tools: Optional list of additional tools (AgentOS tools included by default)
            allow_delegation: Whether agent can delegate to others
            verbose: Enable verbose output
            **kwargs: Additional arguments passed to Agent

        Returns:
            A CrewAI Agent instance
        """
        if not CREWAI_AVAILABLE:
            raise ImportError("CrewAI is not installed")

        # Combine AgentOS tools with any additional tools
        all_tools = self.tools.get_tools()
        if tools:
            all_tools.extend(tools)

        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=all_tools,
            allow_delegation=allow_delegation,
            verbose=verbose,
            **kwargs
        )

    def create_researcher(self, **kwargs) -> Agent:
        """Create a researcher agent with read-only tools"""
        return self.create(
            role="Researcher",
            goal="Find and analyze information from files and the web",
            backstory="You are an expert at finding information from various sources",
            tools=self.tools.get_read_only_tools(),
            **kwargs
        )

    def create_developer(self, **kwargs) -> Agent:
        """Create a developer agent with full tools"""
        return self.create(
            role="Developer",
            goal="Write and modify code to complete tasks",
            backstory="You are a skilled software developer",
            **kwargs
        )

    def create_orchestrator(self, **kwargs) -> Agent:
        """Create an orchestrator agent that can spawn sub-agents"""
        return self.create(
            role="Orchestrator",
            goal="Coordinate tasks and spawn agents as needed",
            backstory="You coordinate complex workflows",
            allow_delegation=True,
            **kwargs
        )

    def disconnect(self):
        """Disconnect from AgentOS"""
        self.tools.disconnect()
