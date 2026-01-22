#!/usr/bin/env python3
"""
Research Team - Clove Multi-Process Version

A TRUE multi-agent system where each agent runs as a separate process:
- Coordinator: Orchestrates via IPC messaging
- Researcher Agent: Separate process for research
- Writer Agent: Separate process for writing

This demonstrates Clove's unique capability: real process isolation with IPC.
"""

import os
import sys
import time
import json
import tempfile
import uuid
from dataclasses import dataclass

# Add Clove SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'agents', 'python_sdk'))

from clove import CloveClient


# =============================================================================
# Agent Scripts (written to temp files and spawned)
# =============================================================================

def get_researcher_agent_code(sdk_path: str, agent_name: str, coordinator_name: str) -> str:
    """Generate researcher agent code"""
    return f'''#!/usr/bin/env python3
"""Researcher Agent - Runs as separate process"""
import sys
sys.path.insert(0, "{sdk_path}")
from clove import CloveClient

def main():
    client = CloveClient()
    if not client.connect():
        return

    # Register as researcher
    client.register_name("{agent_name}")

    import time as t
    # Wait for research requests
    while True:
        result = client.recv_messages(max_messages=1)
        messages = result.get("messages", []) if result else []
        if not messages:
            t.sleep(0.5)
            continue

        for msg in messages:
            data = msg.get("message", {{}})
            if data.get("type") == "research_request":
                topic = data.get("topic", "")
                existing = data.get("existing_notes", "")

                prompt = f"""You are a research assistant. Provide 3-5 key facts about: {{topic}}
Existing notes: {{existing}}
Provide new research findings as bullet points:"""

                result = client.think(prompt, temperature=0.3)

                # Send back to coordinator
                client.send_message(
                    {{"type": "research_result", "notes": result.get("content", "")}},
                    to_name="{coordinator_name}"
                )

            elif data.get("type") == "shutdown":
                break

    client.disconnect()

if __name__ == "__main__":
    main()
'''


def get_writer_agent_code(sdk_path: str, agent_name: str, coordinator_name: str) -> str:
    """Generate writer agent code"""
    return f'''#!/usr/bin/env python3
"""Writer Agent - Runs as separate process"""
import sys
sys.path.insert(0, "{sdk_path}")
from clove import CloveClient

def main():
    client = CloveClient()
    if not client.connect():
        return

    # Register as writer
    client.register_name("{agent_name}")

    import time as t
    # Wait for write requests
    while True:
        result = client.recv_messages(max_messages=1)
        messages = result.get("messages", []) if result else []
        if not messages:
            t.sleep(0.5)
            continue

        for msg in messages:
            data = msg.get("message", {{}})
            if data.get("type") == "write_request":
                topic = data.get("topic", "")
                notes = data.get("research_notes", [])
                all_notes = "\\n\\n".join(notes)

                prompt = f"""You are a technical writer. Synthesize into a clear report (200-300 words).
Topic: {{topic}}
Research Notes:
{{all_notes}}
Write the report:"""

                result = client.think(prompt, temperature=0.7)

                # Send back to coordinator
                client.send_message(
                    {{"type": "write_result", "report": result.get("content", "")}},
                    to_name="{coordinator_name}"
                )

            elif data.get("type") == "shutdown":
                break

    client.disconnect()

if __name__ == "__main__":
    main()
'''


# =============================================================================
# Coordinator (Main Process)
# =============================================================================

class MultiProcessResearchTeam:
    """Clove multi-process research team with real agent isolation"""

    def __init__(self):
        self.client = CloveClient()
        if not self.client.connect():
            raise RuntimeError("Failed to connect to Clove kernel")

        # Use unique ID for this session to avoid name collisions
        self.session_id = uuid.uuid4().hex[:8]

        # Register coordinator with unique name
        self.coordinator_name = f"coordinator_{self.session_id}"
        self.client.register_name(self.coordinator_name)

        self.researcher_agent_id = None
        self.writer_agent_id = None
        self.researcher_name = f"researcher_{self.session_id}"
        self.writer_name = f"writer_{self.session_id}"
        self.temp_files = []

        # SDK path for agent scripts
        self.sdk_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'agents', 'python_sdk'
        ))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._cleanup()

    def _cleanup(self):
        """Kill agents and cleanup"""
        # Send shutdown messages
        try:
            self.client.send_message({"type": "shutdown"}, to_name=self.researcher_name)
            self.client.send_message({"type": "shutdown"}, to_name=self.writer_name)
        except:
            pass

        # Kill agent processes
        if self.researcher_agent_id:
            try:
                self.client.kill(agent_id=self.researcher_agent_id)
            except:
                pass

        if self.writer_agent_id:
            try:
                self.client.kill(agent_id=self.writer_agent_id)
            except:
                pass

        # Cleanup temp files
        for f in self.temp_files:
            try:
                os.unlink(f)
            except:
                pass

        self.client.disconnect()

    def _spawn_agents(self):
        """Spawn researcher and writer as separate processes"""

        # Write researcher agent script
        researcher_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        researcher_file.write(get_researcher_agent_code(self.sdk_path, self.researcher_name, self.coordinator_name))
        researcher_file.close()
        self.temp_files.append(researcher_file.name)

        # Write writer agent script
        writer_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        writer_file.write(get_writer_agent_code(self.sdk_path, self.writer_name, self.coordinator_name))
        writer_file.close()
        self.temp_files.append(writer_file.name)

        # Spawn researcher agent
        result = self.client.spawn(
            name=f"researcher_proc_{self.session_id}",
            script=researcher_file.name,
            sandboxed=False
        )
        if result.get("pid") or result.get("id"):
            self.researcher_agent_id = result.get("id") or result.get("pid")
            print(f"  Spawned researcher agent (ID: {self.researcher_agent_id})")
        else:
            raise RuntimeError(f"Failed to spawn researcher: {result}")

        # Spawn writer agent
        result = self.client.spawn(
            name=f"writer_proc_{self.session_id}",
            script=writer_file.name,
            sandboxed=False
        )
        if result.get("pid") or result.get("id"):
            self.writer_agent_id = result.get("id") or result.get("pid")
            print(f"  Spawned writer agent (ID: {self.writer_agent_id})")
        else:
            raise RuntimeError(f"Failed to spawn writer: {result}")

        # Give agents time to register
        time.sleep(1.0)

    def _coordinator_decide(self, research_notes: list, has_draft: bool) -> str:
        """Coordinator decides next step - uses simple rules if LLM unavailable"""

        # Simple rule-based fallback (matches LLM prompt logic exactly)
        if len(research_notes) == 0:
            return "research"
        elif not has_draft:
            return "write"
        else:
            return "done"

    def _request_research(self, topic: str, existing_notes: list) -> str:
        """Send research request to researcher agent and wait for response"""

        self.client.send_message(
            {
                "type": "research_request",
                "topic": topic,
                "existing_notes": "\n".join(existing_notes) if existing_notes else ""
            },
            to_name=self.researcher_name
        )

        # Wait for response
        for _ in range(120):  # 60 second timeout (120 * 0.5s)
            result = self.client.recv_messages(max_messages=10)
            messages = result.get("messages", []) if result else []
            for msg in messages:
                content = msg.get("message", {})
                if content.get("type") == "research_result":
                    return content.get("notes", "")
            time.sleep(0.5)

        return ""

    def _request_write(self, topic: str, research_notes: list) -> str:
        """Send write request to writer agent and wait for response"""

        self.client.send_message(
            {
                "type": "write_request",
                "topic": topic,
                "research_notes": research_notes
            },
            to_name=self.writer_name
        )

        # Wait for response
        for _ in range(120):  # 60 second timeout (120 * 0.5s)
            result = self.client.recv_messages(max_messages=10)
            messages = result.get("messages", []) if result else []
            for msg in messages:
                content = msg.get("message", {})
                if content.get("type") == "write_result":
                    return content.get("report", "")
            time.sleep(0.5)

        return ""

    def run(self, topic: str, max_iterations: int = 5) -> dict:
        """Run the research workflow with real multi-process agents"""

        print("\nSpawning agent processes...")
        self._spawn_agents()

        research_notes = []
        draft = ""
        final_report = ""
        iteration = 0

        start_time = time.time()

        while iteration < max_iterations:
            # Coordinator decides
            decision = self._coordinator_decide(research_notes, bool(draft))
            iteration += 1

            print(f"  Iteration {iteration}: {decision}")

            if decision == "research":
                # Send to researcher agent (separate process)
                notes = self._request_research(topic, research_notes)
                if notes:
                    research_notes.append(notes)

            elif decision == "write":
                # Send to writer agent (separate process)
                report = self._request_write(topic, research_notes)
                draft = report
                final_report = report

            elif decision == "done":
                break

        end_time = time.time()

        return {
            "topic": topic,
            "final_report": final_report,
            "research_notes": research_notes,
            "iterations": iteration,
            "elapsed_ms": (end_time - start_time) * 1000,
            "agents_spawned": 2
        }


# =============================================================================
# Main
# =============================================================================

def main():
    """Run the Clove multi-process research team"""

    print("=" * 60)
    print("  CLOVE MULTI-PROCESS RESEARCH TEAM")
    print("  (Real process isolation with IPC)")
    print("=" * 60)

    with MultiProcessResearchTeam() as team:
        topic = "The benefits and challenges of microservices architecture"

        print(f"\nTopic: {topic}")
        print("-" * 60)

        result = team.run(topic)

        print(f"\nCompleted in {result['elapsed_ms']:.2f}ms")
        print(f"Iterations: {result['iterations']}")
        print(f"Agents spawned: {result['agents_spawned']}")
        print(f"Research notes collected: {len(result['research_notes'])}")
        print("\n" + "=" * 60)
        print("FINAL REPORT:")
        print("=" * 60)
        print(result['final_report'])

    return result


if __name__ == "__main__":
    main()
