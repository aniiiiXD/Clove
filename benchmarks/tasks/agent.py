"""
Agent Lifecycle Benchmark Tasks

Tests agent spawning, killing, and management overhead.
Only applicable when running through Clove.
"""

import time
import tempfile
import os
from typing import Dict, Any, List


class AgentTasks:
    """Agent lifecycle benchmark operations"""

    def __init__(self, clove_client=None):
        self.clove_client = clove_client
        self.temp_dir = tempfile.mkdtemp(prefix="clove_agent_bench_")

    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_agent_script(self, name: str, duration: float = 1.0) -> str:
        """Create a simple agent script that runs for specified duration"""
        script_path = os.path.join(self.temp_dir, f"{name}.py")
        with open(script_path, 'w') as f:
            f.write(f'''
import time
import sys
sys.path.insert(0, 'agents/python_sdk')

try:
    from clove_sdk import CloveClient
    with CloveClient() as client:
        client.register_name("{name}")
        time.sleep({duration})
except Exception as e:
    print(f"Agent error: {{e}}")
    time.sleep({duration})
''')
        return script_path

    def spawn_and_kill(self, sandboxed: bool = False) -> Dict[str, Any]:
        """Spawn an agent and immediately kill it"""
        if not self.clove_client:
            return {"success": False, "error": "Clove client required", "native_equivalent": "N/A"}

        # Create agent script
        script_path = self._create_agent_script("bench_agent", duration=5.0)

        # Spawn
        spawn_start = time.perf_counter()
        result = self.clove_client.spawn(
            name="bench_agent",
            script=script_path,
            sandboxed=sandboxed
        )
        spawn_time = (time.perf_counter() - spawn_start) * 1000

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Spawn failed"),
                "spawn_time_ms": spawn_time,
            }

        agent_id = result.get("id")
        time.sleep(0.1)  # Brief pause to let agent start

        # Kill
        kill_start = time.perf_counter()
        kill_result = self.clove_client.kill(agent_id=agent_id)
        kill_time = (time.perf_counter() - kill_start) * 1000

        return {
            "success": True,
            "agent_id": agent_id,
            "sandboxed": sandboxed,
            "spawn_time_ms": spawn_time,
            "kill_time_ms": kill_time,
            "total_time_ms": spawn_time + kill_time,
        }

    def spawn_multiple(self, count: int, sandboxed: bool = False) -> Dict[str, Any]:
        """Spawn multiple agents concurrently"""
        if not self.clove_client:
            return {"success": False, "error": "Clove client required"}

        agent_ids = []
        spawn_times = []

        # Spawn all agents
        for i in range(count):
            script_path = self._create_agent_script(f"multi_agent_{i}", duration=5.0)

            spawn_start = time.perf_counter()
            result = self.clove_client.spawn(
                name=f"multi_agent_{i}",
                script=script_path,
                sandboxed=sandboxed
            )
            spawn_time = (time.perf_counter() - spawn_start) * 1000
            spawn_times.append(spawn_time)

            if result.get("success"):
                agent_ids.append(result.get("id"))

        time.sleep(0.2)  # Let agents start

        # Kill all agents
        kill_times = []
        for agent_id in agent_ids:
            kill_start = time.perf_counter()
            self.clove_client.kill(agent_id=agent_id)
            kill_time = (time.perf_counter() - kill_start) * 1000
            kill_times.append(kill_time)

        return {
            "success": len(agent_ids) == count,
            "requested": count,
            "spawned": len(agent_ids),
            "avg_spawn_time_ms": sum(spawn_times) / len(spawn_times) if spawn_times else 0,
            "avg_kill_time_ms": sum(kill_times) / len(kill_times) if kill_times else 0,
            "total_spawn_time_ms": sum(spawn_times),
            "total_kill_time_ms": sum(kill_times),
        }

    def list_agents(self) -> Dict[str, Any]:
        """List all running agents"""
        if not self.clove_client:
            return {"success": False, "error": "Clove client required"}

        start = time.perf_counter()
        result = self.clove_client.list_agents()
        duration = (time.perf_counter() - start) * 1000

        return {
            "success": True,
            "agent_count": len(result) if isinstance(result, list) else 0,
            "list_time_ms": duration,
        }

    def get_agent_metrics(self, agent_id: int = None) -> Dict[str, Any]:
        """Get metrics for an agent"""
        if not self.clove_client:
            return {"success": False, "error": "Clove client required"}

        start = time.perf_counter()
        if agent_id:
            result = self.clove_client.get_agent_metrics(agent_id=agent_id)
        else:
            result = self.clove_client.get_all_agent_metrics()
        duration = (time.perf_counter() - start) * 1000

        return {
            "success": result.get("success", False),
            "metrics_time_ms": duration,
            "metrics": result.get("metrics") or result.get("agents"),
        }
