"""
IPC (Inter-Process Communication) Benchmark Tasks

Tests messaging between agents.
Only applicable when running through Clove.
"""

import time
import tempfile
import os
import threading
from typing import Dict, Any


class IPCTasks:
    """IPC benchmark operations"""

    def __init__(self, clove_client=None):
        self.clove_client = clove_client
        self.temp_dir = tempfile.mkdtemp(prefix="clove_ipc_bench_")

    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_echo_agent(self, name: str) -> str:
        """Create an agent that echoes messages back"""
        script_path = os.path.join(self.temp_dir, f"{name}.py")
        with open(script_path, 'w') as f:
            f.write(f'''
import time
import sys
sys.path.insert(0, 'agents/python_sdk')

from clove_sdk import CloveClient

with CloveClient() as client:
    client.register_name("{name}")

    # Echo messages for 10 seconds
    end_time = time.time() + 10
    while time.time() < end_time:
        result = client.recv_messages()
        if result.get("success"):
            for msg in result.get("messages", []):
                # Echo back
                client.send_message(
                    {{"echo": msg.get("data"), "from": "{name}"}},
                    to=msg.get("from_agent_id")
                )
        time.sleep(0.01)
''')
        return script_path

    def message_roundtrip(self, message_size: int = 1024) -> Dict[str, Any]:
        """Send a message and measure roundtrip time"""
        if not self.clove_client:
            return {"success": False, "error": "Clove client required"}

        # Create and spawn echo agent
        script_path = self._create_echo_agent("echo_agent")
        spawn_result = self.clove_client.spawn(
            name="echo_agent",
            script=script_path,
            sandboxed=False
        )

        if not spawn_result.get("success"):
            return {"success": False, "error": "Failed to spawn echo agent"}

        agent_id = spawn_result.get("id")
        time.sleep(0.3)  # Let agent register

        # Register ourselves
        self.clove_client.register_name("bench_sender")

        # Send message and measure roundtrip
        message = {"data": "x" * message_size, "timestamp": time.time()}

        start = time.perf_counter()
        send_result = self.clove_client.send_message(message, to_name="echo_agent")

        if not send_result.get("success"):
            self.clove_client.kill(agent_id=agent_id)
            return {"success": False, "error": "Send failed"}

        # Wait for response
        response = None
        timeout = time.time() + 5
        while time.time() < timeout:
            recv_result = self.clove_client.recv_messages()
            if recv_result.get("success") and recv_result.get("messages"):
                response = recv_result.get("messages")[0]
                break
            time.sleep(0.01)

        roundtrip_time = (time.perf_counter() - start) * 1000

        # Cleanup
        self.clove_client.kill(agent_id=agent_id)

        if response:
            return {
                "success": True,
                "message_size": message_size,
                "roundtrip_ms": roundtrip_time,
            }
        else:
            return {
                "success": False,
                "error": "No response received",
                "roundtrip_ms": roundtrip_time,
            }

    def broadcast_test(self, agent_count: int = 3, message_size: int = 512) -> Dict[str, Any]:
        """Broadcast message to multiple agents"""
        if not self.clove_client:
            return {"success": False, "error": "Clove client required"}

        # Spawn multiple listener agents
        agent_ids = []
        for i in range(agent_count):
            script_path = self._create_echo_agent(f"listener_{i}")
            result = self.clove_client.spawn(
                name=f"listener_{i}",
                script=script_path,
                sandboxed=False
            )
            if result.get("success"):
                agent_ids.append(result.get("id"))

        time.sleep(0.5)  # Let agents register

        # Broadcast message
        message = {"broadcast_data": "x" * message_size}

        start = time.perf_counter()
        result = self.clove_client.broadcast(message)
        broadcast_time = (time.perf_counter() - start) * 1000

        # Cleanup
        for agent_id in agent_ids:
            self.clove_client.kill(agent_id=agent_id)

        return {
            "success": result.get("success", False),
            "agent_count": len(agent_ids),
            "message_size": message_size,
            "broadcast_time_ms": broadcast_time,
        }

    def state_store_ops(self, key_count: int = 100) -> Dict[str, Any]:
        """Benchmark state store operations"""
        if not self.clove_client:
            return {"success": False, "error": "Clove client required"}

        # Write keys
        write_start = time.perf_counter()
        for i in range(key_count):
            self.clove_client.store(f"bench_key_{i}", {"value": i, "data": "x" * 100})
        write_time = (time.perf_counter() - write_start) * 1000

        # Read keys
        read_start = time.perf_counter()
        for i in range(key_count):
            self.clove_client.fetch(f"bench_key_{i}")
        read_time = (time.perf_counter() - read_start) * 1000

        # List keys
        list_start = time.perf_counter()
        self.clove_client.list_keys(prefix="bench_key_")
        list_time = (time.perf_counter() - list_start) * 1000

        # Delete keys
        delete_start = time.perf_counter()
        for i in range(key_count):
            self.clove_client.delete_key(f"bench_key_{i}")
        delete_time = (time.perf_counter() - delete_start) * 1000

        return {
            "success": True,
            "key_count": key_count,
            "write_time_ms": write_time,
            "read_time_ms": read_time,
            "list_time_ms": list_time,
            "delete_time_ms": delete_time,
            "avg_write_ms": write_time / key_count,
            "avg_read_ms": read_time / key_count,
        }
