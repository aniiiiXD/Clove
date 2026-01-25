"""
Clove Runner

Executes benchmark tasks through the Clove kernel.
"""

import sys
import os
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'python_sdk'))

from config import BenchmarkConfig, TaskCategory, TaskConfig
from metrics import BenchmarkResults, MetricsCollector, TaskTimer


class CloveRunner:
    """Runs benchmarks through Clove kernel"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results = BenchmarkResults(
            benchmark_name=config.name,
            start_time=datetime.now(),
            runner_type="clove"
        )
        self.metrics_collector = MetricsCollector(interval=config.metrics_interval)
        self.clove_client = None
        self.spawned_agents = []

    def connect(self) -> bool:
        """Connect to Clove kernel"""
        try:
            from clove_sdk import CloveClient
            self.clove_client = CloveClient()
            if not self.clove_client.connect():
                print("ERROR: Failed to connect to Clove kernel")
                print("Make sure the kernel is running: ./build/clove_kernel")
                return False
            return True
        except Exception as e:
            print(f"ERROR: Could not connect to Clove: {e}")
            return False

    def disconnect(self):
        """Disconnect from Clove kernel"""
        # Kill any spawned agents
        for agent_id in self.spawned_agents:
            try:
                self.clove_client.kill(agent_id=agent_id)
            except:
                pass
        self.spawned_agents = []

        if self.clove_client:
            self.clove_client.disconnect()
            self.clove_client = None

    def run(self) -> BenchmarkResults:
        """Run all configured benchmark tasks"""
        print(f"\n{'='*60}")
        print(f"  CLOVE BENCHMARK: {self.config.name}")
        print(f"{'='*60}\n")

        if not self.connect():
            return self.results

        if self.config.collect_system_metrics:
            self.metrics_collector.start_collection(use_clove=True)

        try:
            for task_config in self.config.tasks:
                self._run_task(task_config)
        finally:
            if self.config.collect_system_metrics:
                snapshots = self.metrics_collector.stop_collection()
                self.results.system_snapshots = snapshots

            self.disconnect()

        self.results.end_time = datetime.now()
        self.results.compute_statistics()

        return self.results

    def _run_task(self, task_config: TaskConfig):
        """Run a single task with all iterations"""
        print(f"Running: {task_config.name} ({task_config.description})")
        print(f"  Category: {task_config.category.value}")
        print(f"  Iterations: {task_config.warmup_iterations} warmup + {task_config.iterations} measured")

        # Warmup iterations
        for i in range(task_config.warmup_iterations):
            self._execute_task(task_config, iteration=-(task_config.warmup_iterations - i))

        # Measured iterations
        for i in range(task_config.iterations):
            with TaskTimer(task_config.name, i) as timer:
                result = self._execute_task(task_config, iteration=i)
                timer.extra = result if isinstance(result, dict) else {}

            self.results.add_task_metric(timer.to_metric())

            if (i + 1) % 5 == 0 or i == task_config.iterations - 1:
                print(f"  Progress: {i + 1}/{task_config.iterations}")

        print(f"  Done\n")

    def _execute_task(self, task_config: TaskConfig, iteration: int) -> Optional[dict]:
        """Execute a single task iteration"""
        params = task_config.params

        if task_config.category == TaskCategory.AGENT_SPAWN:
            return self._spawn_agent(params)

        elif task_config.category == TaskCategory.LLM_CALL:
            return self._llm_call(params)

        elif task_config.category == TaskCategory.TOOL_EXECUTION:
            return self._tool_execution(params)

        elif task_config.category == TaskCategory.MULTI_AGENT:
            return self._multi_agent(params)

        elif task_config.category == TaskCategory.MEMORY:
            return self._memory_ops(params)

        elif task_config.category == TaskCategory.END_TO_END:
            return self._end_to_end(params)

        return {"success": True}

    def _spawn_agent(self, params: dict) -> dict:
        """Spawn a new Clove agent"""
        try:
            agent_count = params.get("agent_count", 1)
            spawned = []

            for _ in range(agent_count):
                result = self.clove_client.spawn(sandbox=params.get("sandboxed", False))
                if result.get("success"):
                    agent_id = result.get("agent_id")
                    spawned.append(agent_id)
                    self.spawned_agents.append(agent_id)

            # Kill the spawned agents to reset state
            for agent_id in spawned:
                self.clove_client.kill(agent_id=agent_id)
                self.spawned_agents.remove(agent_id)

            return {"success": True, "spawned": len(spawned)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _llm_call(self, params: dict) -> dict:
        """Make an LLM call through Clove"""
        try:
            prompt = params.get("prompt", "Hello")
            max_tokens = params.get("max_tokens", 100)

            result = self.clove_client.think(
                prompt=prompt,
                temperature=0.7
            )

            return {
                "success": result.get("success", False),
                "tokens": result.get("tokens", 0)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_execution(self, params: dict) -> dict:
        """Execute a tool through Clove"""
        try:
            tool = params.get("tool", "echo")
            tool_input = params.get("input", "test")

            if tool == "echo":
                result = self.clove_client.echo(tool_input)
                return {"success": True, "result": result}
            elif tool == "calculator":
                # Use exec for calculation
                result = self.clove_client.exec(f"python3 -c \"print({tool_input})\"")
                return {"success": result.get("success", False), "result": result.get("stdout", "")}
            else:
                # Generic tool via echo
                result = self.clove_client.echo(f"{tool}: {tool_input}")
                return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _multi_agent(self, params: dict) -> dict:
        """Multi-agent coordination through Clove"""
        try:
            agent_count = params.get("agent_count", 2)
            message = params.get("task", "hello")
            message_size = params.get("message_size", 256)

            # Spawn agents
            agents = []
            for _ in range(agent_count):
                result = self.clove_client.spawn()
                if result.get("success"):
                    agents.append(result.get("agent_id"))

            # Register names and send messages
            for i, agent_id in enumerate(agents):
                # Each agent would need its own connection in real scenario
                # For benchmark, we measure the IPC overhead
                pass

            # Message passing simulation using state store
            for i in range(agent_count - 1):
                self.clove_client.state_set(f"msg_{i}", message[:message_size])
                self.clove_client.state_get(f"msg_{i}")

            # Cleanup
            for agent_id in agents:
                self.clove_client.kill(agent_id=agent_id)

            return {"success": True, "agent_count": len(agents)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _memory_ops(self, params: dict) -> dict:
        """Memory/state operations through Clove"""
        try:
            key_count = params.get("key_count", 10)

            # Store items
            for i in range(key_count):
                self.clove_client.state_set(f"bench_key_{i}", f"value_{i}")

            # Retrieve items
            for i in range(key_count):
                self.clove_client.state_get(f"bench_key_{i}")

            # Cleanup
            for i in range(key_count):
                self.clove_client.state_delete(f"bench_key_{i}")

            return {"success": True, "stored": key_count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _end_to_end(self, params: dict) -> dict:
        """End-to-end agent task through Clove"""
        try:
            question = params.get("question", params.get("topic", "Hello"))

            # Full agent workflow: spawn -> think -> respond
            spawn_result = self.clove_client.spawn()
            if not spawn_result.get("success"):
                return {"success": False, "error": "Failed to spawn agent"}

            agent_id = spawn_result.get("agent_id")

            # Make LLM call
            think_result = self.clove_client.think(prompt=question)

            # Cleanup
            self.clove_client.kill(agent_id=agent_id)

            return {
                "success": think_result.get("success", False),
                "tokens": think_result.get("tokens", 0)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """Run Clove benchmark"""
    from config import get_quick_config

    config = get_quick_config()
    runner = CloveRunner(config)
    results = runner.run()

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)

    for task_name, stats in results.statistics.items():
        print(f"\n{task_name}:")
        print(f"  Mean: {stats['mean_ms']:.2f}ms")
        print(f"  Median: {stats['median_ms']:.2f}ms")
        print(f"  P95: {stats['p95_ms']:.2f}ms")

    filepath = results.save(config.output_dir)
    print(f"\nResults saved to: {filepath}")


if __name__ == "__main__":
    main()
