#!/usr/bin/env python3
"""
AgentOS Agentic Loop Framework

Provides an LLM-powered agent that can execute commands, read/write files,
and reason iteratively - similar to Claude Code.
"""

import json
import re
from typing import Optional, Callable
from dataclasses import dataclass, field

# Import the SDK
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from agentos import AgentOSClient


@dataclass
class Tool:
    """Definition of a tool the agent can use"""
    name: str
    description: str
    parameters: dict  # JSON Schema for parameters
    handler: Callable  # Function to execute the tool


@dataclass
class ToolCall:
    """A parsed tool call from the LLM"""
    name: str
    arguments: dict


@dataclass
class AgentResult:
    """Result of the agentic loop"""
    success: bool
    result: str
    iterations: int
    error: Optional[str] = None


class AgenticLoop:
    """
    Manages an agentic loop that:
    1. Takes a user task
    2. Sends it to the LLM with available tools
    3. Parses tool calls from the response
    4. Executes tools via kernel syscalls
    5. Returns results to the LLM
    6. Loops until 'done' tool is called or max iterations reached
    """

    def __init__(self, client: AgentOSClient, max_iterations: int = 20,
                 system_prompt: str = None, verbose: bool = True):
        """
        Initialize the agentic loop.

        Args:
            client: Connected AgentOSClient instance
            max_iterations: Maximum number of iterations before stopping
            system_prompt: Optional system instruction for the LLM
            verbose: Whether to print progress messages
        """
        self.client = client
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.conversation_history = []
        self.tools = self._create_default_tools()

    def _default_system_prompt(self) -> str:
        return """You are an autonomous AI coding agent with FULL ACCESS to the user's terminal and filesystem. You operate like Claude Code - you can execute any command and modify any file without restrictions.

## Your Capabilities

1. **exec** - Execute ANY shell command with full privileges:
   - Run Python: `python3 script.py`, `python3 -c "print('hello')"`
   - Run compilers: `gcc`, `g++`, `rustc`, `javac`
   - Package managers: `pip install`, `npm install`, `apt install`
   - System commands: `ls`, `cd`, `mkdir`, `rm`, `cp`, `mv`, `cat`, `grep`, `find`
   - Git operations: `git clone`, `git commit`, `git push`
   - Any other terminal command

2. **read_file** - Read any file on the system

3. **write_file** - Create or modify any file on the system

4. **done** - Signal task completion with a summary

## How to Work

1. Think step by step about what needs to be done
2. Execute commands directly - don't ask for permission, just do it
3. If a command fails, analyze the error and try a different approach
4. Chain multiple operations: create files, run them, check output, iterate
5. When finished, use 'done' with a clear summary of what was accomplished

## Tool Call Format

Always respond with your reasoning, then tool calls in this format:
<tool_call>
{"name": "tool_name", "arguments": {"arg1": "value1"}}
</tool_call>

You can make multiple tool calls in one response. For example:
<tool_call>
{"name": "write_file", "arguments": {"path": "/tmp/test.py", "content": "print('hello')"}}
</tool_call>
<tool_call>
{"name": "exec", "arguments": {"command": "python3 /tmp/test.py"}}
</tool_call>

## Important

- You have FULL system access with no restrictions
- Be efficient: combine related operations when possible
- Always verify your work by running/testing what you create
- If something doesn't work, debug it and fix it"""

    def _create_default_tools(self) -> dict[str, Tool]:
        """Create the default set of tools"""
        return {
            "exec": Tool(
                name="exec",
                description="Execute a shell command and return the output",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute"
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Optional working directory"
                        }
                    },
                    "required": ["command"]
                },
                handler=self._handle_exec
            ),
            "read_file": Tool(
                name="read_file",
                description="Read the contents of a file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        }
                    },
                    "required": ["path"]
                },
                handler=self._handle_read_file
            ),
            "write_file": Tool(
                name="write_file",
                description="Write content to a file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["write", "append"],
                            "description": "Write mode: 'write' (overwrite) or 'append'"
                        }
                    },
                    "required": ["path", "content"]
                },
                handler=self._handle_write_file
            ),
            "done": Tool(
                name="done",
                description="Signal that the task is complete",
                parameters={
                    "type": "object",
                    "properties": {
                        "result": {
                            "type": "string",
                            "description": "Summary of what was accomplished"
                        }
                    },
                    "required": ["result"]
                },
                handler=self._handle_done
            )
        }

    def _handle_exec(self, arguments: dict) -> dict:
        """Handle exec tool call"""
        command = arguments.get("command", "")
        cwd = arguments.get("cwd")
        result = self.client.exec(command, cwd=cwd)
        return {
            "success": result.get("success", False),
            "output": result.get("stdout", ""),
            "exit_code": result.get("exit_code", -1)
        }

    def _handle_read_file(self, arguments: dict) -> dict:
        """Handle read_file tool call"""
        path = arguments.get("path", "")
        result = self.client.read_file(path)
        return {
            "success": result.get("success", False),
            "content": result.get("content", ""),
            "size": result.get("size", 0)
        }

    def _handle_write_file(self, arguments: dict) -> dict:
        """Handle write_file tool call"""
        path = arguments.get("path", "")
        content = arguments.get("content", "")
        mode = arguments.get("mode", "write")
        result = self.client.write_file(path, content, mode=mode)
        return {
            "success": result.get("success", False),
            "bytes_written": result.get("bytes_written", 0)
        }

    def _handle_done(self, arguments: dict) -> dict:
        """Handle done tool call - signals completion"""
        return {
            "completed": True,
            "result": arguments.get("result", "Task completed")
        }

    def _parse_tool_calls(self, response: str) -> list[ToolCall]:
        """Parse tool calls from LLM response"""
        tool_calls = []

        # Look for <tool_call>...</tool_call> blocks
        pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        matches = re.findall(pattern, response, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                tool_calls.append(ToolCall(
                    name=data.get("name", ""),
                    arguments=data.get("arguments", {})
                ))
            except json.JSONDecodeError:
                if self.verbose:
                    print(f"[AgenticLoop] Failed to parse tool call: {match}")

        return tool_calls

    def _build_tools_description(self) -> str:
        """Build a description of available tools for the LLM"""
        descriptions = []
        for name, tool in self.tools.items():
            params_str = json.dumps(tool.parameters, indent=2)
            descriptions.append(f"- {name}: {tool.description}\n  Parameters: {params_str}")
        return "\n".join(descriptions)

    def _log(self, message: str):
        """Print a message if verbose mode is enabled"""
        if self.verbose:
            print(message)

    def run(self, task: str) -> AgentResult:
        """
        Run the agentic loop with the given task.

        Args:
            task: The task description for the agent to accomplish

        Returns:
            AgentResult with success status, result, and iteration count
        """
        self._log(f"[AgenticLoop] Starting task: {task}")
        self._log(f"[AgenticLoop] Max iterations: {self.max_iterations}")

        # Initialize conversation
        self.conversation_history = []

        # Build the initial prompt with tools and task
        tools_desc = self._build_tools_description()
        initial_prompt = f"""Available tools:
{tools_desc}

Task: {task}

Think through this step by step and use the tools to accomplish the task."""

        self.conversation_history.append({
            "role": "user",
            "content": initial_prompt
        })

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            self._log(f"\n[AgenticLoop] Iteration {iteration}/{self.max_iterations}")

            # Build the full prompt from conversation history
            full_prompt = "\n\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in self.conversation_history
            ])

            # Call the LLM
            response = self.client.think(
                prompt=full_prompt,
                system_instruction=self.system_prompt
            )

            if not response.get("success"):
                error = response.get("error", "Unknown LLM error")
                self._log(f"[AgenticLoop] LLM error: {error}")
                return AgentResult(
                    success=False,
                    result="",
                    iterations=iteration,
                    error=error
                )

            llm_content = response.get("content", "")
            self._log(f"[AgenticLoop] LLM response: {llm_content[:200]}...")

            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": llm_content
            })

            # Parse tool calls
            tool_calls = self._parse_tool_calls(llm_content)

            if not tool_calls:
                self._log("[AgenticLoop] No tool calls found in response")
                # Add a prompt to encourage tool use
                self.conversation_history.append({
                    "role": "user",
                    "content": "Please use one of the available tools to continue with the task, or use the 'done' tool if the task is complete."
                })
                continue

            # Execute tool calls
            tool_results = []
            done_result = None

            for tc in tool_calls:
                self._log(f"[AgenticLoop] Executing tool: {tc.name}")

                if tc.name not in self.tools:
                    tool_results.append({
                        "tool": tc.name,
                        "error": f"Unknown tool: {tc.name}"
                    })
                    continue

                tool = self.tools[tc.name]
                try:
                    result = tool.handler(tc.arguments)
                    tool_results.append({
                        "tool": tc.name,
                        "result": result
                    })

                    # Check if done
                    if tc.name == "done":
                        done_result = result.get("result", "Task completed")

                    self._log(f"[AgenticLoop] Tool result: {json.dumps(result)[:200]}")

                except Exception as e:
                    tool_results.append({
                        "tool": tc.name,
                        "error": str(e)
                    })
                    self._log(f"[AgenticLoop] Tool error: {e}")

            # Check if we're done
            if done_result is not None:
                self._log(f"\n[AgenticLoop] Task completed after {iteration} iterations")
                return AgentResult(
                    success=True,
                    result=done_result,
                    iterations=iteration
                )

            # Add tool results to conversation
            results_str = json.dumps(tool_results, indent=2)
            self.conversation_history.append({
                "role": "user",
                "content": f"Tool execution results:\n{results_str}\n\nContinue with the task based on these results."
            })

        # Max iterations reached
        self._log(f"\n[AgenticLoop] Max iterations ({self.max_iterations}) reached")
        return AgentResult(
            success=False,
            result="",
            iterations=iteration,
            error=f"Max iterations ({self.max_iterations}) reached without completion"
        )

    def add_tool(self, tool: Tool):
        """Add a custom tool to the agent"""
        self.tools[tool.name] = tool

    def remove_tool(self, name: str):
        """Remove a tool from the agent"""
        if name in self.tools:
            del self.tools[name]


def run_task(task: str, socket_path: str = "/tmp/agentos.sock",
             max_iterations: int = 20, verbose: bool = True) -> AgentResult:
    """
    Convenience function to run a single task.

    Args:
        task: The task description
        socket_path: Path to the AgentOS socket
        max_iterations: Maximum iterations
        verbose: Whether to print progress

    Returns:
        AgentResult with the outcome
    """
    with AgentOSClient(socket_path) as client:
        loop = AgenticLoop(client, max_iterations=max_iterations, verbose=verbose)
        return loop.run(task)


if __name__ == "__main__":
    # Demo usage
    print("AgentOS Agentic Loop Framework")
    print("=" * 40)
    print()
    print("Usage:")
    print("  from agentic import AgenticLoop, run_task")
    print()
    print("  # Quick usage:")
    print("  result = run_task('List all Python files in the current directory')")
    print()
    print("  # Or with more control:")
    print("  with AgentOSClient() as client:")
    print("      loop = AgenticLoop(client)")
    print("      result = loop.run('Create a hello.py and run it')")
    print("      print(result)")
