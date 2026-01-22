#!/usr/bin/env python3
"""
Research Team - Clove Version

A multi-agent system with:
- Coordinator: Orchestrates the research workflow
- Researcher: Gathers information on topics
- Writer: Synthesizes findings into a report

This demonstrates Clove's kernel-mediated LLM calls and state management.
"""

import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

# Add Clove SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'agents', 'python_sdk'))

from clove import CloveClient


# =============================================================================
# State Management
# =============================================================================

@dataclass
class ResearchState:
    """State shared across all agents"""
    topic: str
    research_notes: list
    draft: str
    final_report: str
    current_step: str
    iteration: int
    max_iterations: int


# =============================================================================
# Agent Definitions
# =============================================================================

class ResearchTeam:
    """Clove-based multi-agent research team"""

    def __init__(self):
        self.client = CloveClient()
        if not self.client.connect():
            raise RuntimeError("Failed to connect to Clove kernel")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.disconnect()

    def _coordinator_decide(self, state: ResearchState) -> str:
        """Coordinator decides next step using Clove's think()"""

        context = f"""
Topic: {state.topic}
Current Step: {state.current_step}
Iteration: {state.iteration}/{state.max_iterations}
Research Notes: {len(state.research_notes)} items
Draft exists: {bool(state.draft)}
"""

        prompt = f"""You are a research coordinator. Based on the current state, decide the next action:
- If no research has been done, respond with "RESEARCH"
- If research exists but no draft, respond with "WRITE"
- If draft exists, respond with "DONE"
Only respond with one word: RESEARCH, WRITE, or DONE

Current State:
{context}"""

        result = self.client.think(prompt, temperature=0)

        if result.get("success"):
            decision = result.get("content", "").strip().upper()
            if "RESEARCH" in decision:
                return "research"
            elif "WRITE" in decision:
                return "write"
            else:
                return "done"
        return "done"

    def _researcher_gather(self, state: ResearchState) -> str:
        """Researcher gathers information using Clove's think()"""

        existing_notes = "\n".join(state.research_notes) if state.research_notes else "None yet"

        prompt = f"""You are a research assistant. Provide 3-5 key facts or insights about the given topic.
Be concise and factual. Format as bullet points.

Topic: {state.topic}

Existing notes:
{existing_notes}

Provide new research findings:"""

        result = self.client.think(prompt, temperature=0.3)

        if result.get("success"):
            return result.get("content", "")
        return ""

    def _writer_synthesize(self, state: ResearchState) -> str:
        """Writer synthesizes research into report using Clove's think()"""

        all_notes = "\n\n".join(state.research_notes)

        prompt = f"""You are a technical writer. Synthesize the research notes into a clear, well-structured report.
Include an introduction, main findings, and conclusion. Keep it concise (200-300 words).

Topic: {state.topic}

Research Notes:
{all_notes}

Write the report:"""

        result = self.client.think(prompt, temperature=0.7)

        if result.get("success"):
            return result.get("content", "")
        return ""

    def run(self, topic: str, max_iterations: int = 5) -> dict:
        """Run the research workflow"""

        state = ResearchState(
            topic=topic,
            research_notes=[],
            draft="",
            final_report="",
            current_step="start",
            iteration=0,
            max_iterations=max_iterations
        )

        start_time = time.time()

        while state.iteration < state.max_iterations:
            # Coordinator decides next step
            decision = self._coordinator_decide(state)
            state.current_step = decision
            state.iteration += 1

            if decision == "research":
                # Researcher gathers information
                notes = self._researcher_gather(state)
                if notes:
                    state.research_notes.append(notes)

            elif decision == "write":
                # Writer synthesizes report
                report = self._writer_synthesize(state)
                state.draft = report
                state.final_report = report

            elif decision == "done":
                break

        end_time = time.time()

        return {
            "topic": topic,
            "final_report": state.final_report,
            "research_notes": state.research_notes,
            "iterations": state.iteration,
            "elapsed_ms": (end_time - start_time) * 1000
        }


# =============================================================================
# Main
# =============================================================================

def main():
    """Run the Clove research team"""

    print("=" * 60)
    print("  CLOVE RESEARCH TEAM")
    print("=" * 60)

    # Create team
    with ResearchTeam() as team:
        # Run research
        topic = "The benefits and challenges of microservices architecture"

        print(f"\nTopic: {topic}")
        print("-" * 60)

        result = team.run(topic)

        print(f"\nCompleted in {result['elapsed_ms']:.2f}ms")
        print(f"Iterations: {result['iterations']}")
        print(f"Research notes collected: {len(result['research_notes'])}")
        print("\n" + "=" * 60)
        print("FINAL REPORT:")
        print("=" * 60)
        print(result['final_report'])

    return result


if __name__ == "__main__":
    main()
