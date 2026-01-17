"""
AgentOS Framework Adapters

This package provides adapters for popular AI agent frameworks:
- LangChain: langchain_adapter.py
- CrewAI: crewai_adapter.py
- AutoGen: autogen_adapter.py

Each adapter exposes AgentOS syscalls as native framework components.
"""

from .langchain_adapter import (
    AgentOSToolkit,
    AgentOSReadTool,
    AgentOSWriteTool,
    AgentOSExecTool,
    AgentOSThinkTool,
    AgentOSSpawnTool,
    AgentOSHTTPTool,
)

from .crewai_adapter import (
    AgentOSCrewAgent,
    AgentOSCrewTools,
)

from .autogen_adapter import (
    AgentOSAssistant,
    AgentOSUserProxy,
)

__all__ = [
    # LangChain
    "AgentOSToolkit",
    "AgentOSReadTool",
    "AgentOSWriteTool",
    "AgentOSExecTool",
    "AgentOSThinkTool",
    "AgentOSSpawnTool",
    "AgentOSHTTPTool",
    # CrewAI
    "AgentOSCrewAgent",
    "AgentOSCrewTools",
    # AutoGen
    "AgentOSAssistant",
    "AgentOSUserProxy",
]
