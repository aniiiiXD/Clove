#!/usr/bin/env python3
"""
Research Team - LangGraph Version

A multi-agent system with:
- Coordinator: Orchestrates the research workflow
- Researcher: Gathers information on topics
- Writer: Synthesizes findings into a report

This demonstrates LangGraph's StateGraph pattern for multi-agent coordination.
"""

import os
import sys
import time
from typing import TypedDict, Annotated, Literal
from dataclasses import dataclass

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END


def invoke_with_retry(llm, messages, max_retries=3, base_delay=5):
    """Invoke LLM with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"    Rate limited, waiting {delay}s...")
                    time.sleep(delay)
                else:
                    raise
            else:
                raise


# =============================================================================
# State Definition
# =============================================================================

class ResearchState(TypedDict):
    """State shared across all agents"""
    topic: str
    research_notes: list[str]
    draft: str
    final_report: str
    current_step: str
    iteration: int
    max_iterations: int


# =============================================================================
# Agent Definitions
# =============================================================================

class ResearchTeam:
    """LangGraph-based multi-agent research team"""

    def __init__(self):
        # Get API key
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("No API key found (GOOGLE_API_KEY or GEMINI_API_KEY)")

        # Use gemini-2.0-flash model
        model_name = "gemini-2.0-flash"

        # Use GEMINI_API_KEY as primary (separate quota)
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        # Initialize single LLM to share quota better
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            google_api_key=api_key
        )

        # Aliases for different "agents" (same LLM, different prompts)
        self.coordinator_llm = self.llm
        self.researcher_llm = self.llm
        self.writer_llm = self.llm

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""

        workflow = StateGraph(ResearchState)

        # Add nodes
        workflow.add_node("coordinator", self._coordinator_node)
        workflow.add_node("researcher", self._researcher_node)
        workflow.add_node("writer", self._writer_node)

        # Set entry point
        workflow.set_entry_point("coordinator")

        # Add conditional edges from coordinator
        workflow.add_conditional_edges(
            "coordinator",
            self._route_from_coordinator,
            {
                "researcher": "researcher",
                "writer": "writer",
                "end": END
            }
        )

        # Researcher always goes back to coordinator
        workflow.add_edge("researcher", "coordinator")

        # Writer always goes back to coordinator
        workflow.add_edge("writer", "coordinator")

        return workflow.compile()

    def _coordinator_node(self, state: ResearchState) -> ResearchState:
        """Coordinator decides next step"""

        # Build context for coordinator
        context = f"""
Topic: {state['topic']}
Current Step: {state['current_step']}
Iteration: {state['iteration']}/{state['max_iterations']}
Research Notes: {len(state['research_notes'])} items
Draft exists: {bool(state['draft'])}
"""

        messages = [
            SystemMessage(content="""You are a research coordinator. Based on the current state, decide the next action:
- If no research has been done, respond with "RESEARCH"
- If research exists but no draft, respond with "WRITE"
- If draft exists, respond with "DONE"
Only respond with one word: RESEARCH, WRITE, or DONE"""),
            HumanMessage(content=context)
        ]

        response = invoke_with_retry(self.coordinator_llm, messages)
        decision = response.content.strip().upper()

        new_state = dict(state)
        new_state['iteration'] = state['iteration'] + 1

        if "RESEARCH" in decision:
            new_state['current_step'] = "research"
        elif "WRITE" in decision:
            new_state['current_step'] = "write"
        else:
            new_state['current_step'] = "done"

        return new_state

    def _researcher_node(self, state: ResearchState) -> ResearchState:
        """Researcher gathers information"""

        existing_notes = "\n".join(state['research_notes']) if state['research_notes'] else "None yet"

        messages = [
            SystemMessage(content="""You are a research assistant. Provide 3-5 key facts or insights about the given topic.
Be concise and factual. Format as bullet points."""),
            HumanMessage(content=f"Topic: {state['topic']}\n\nExisting notes:\n{existing_notes}\n\nProvide new research findings:")
        ]

        response = invoke_with_retry(self.researcher_llm, messages)

        new_state = dict(state)
        new_state['research_notes'] = state['research_notes'] + [response.content]

        return new_state

    def _writer_node(self, state: ResearchState) -> ResearchState:
        """Writer synthesizes research into report"""

        all_notes = "\n\n".join(state['research_notes'])

        messages = [
            SystemMessage(content="""You are a technical writer. Synthesize the research notes into a clear, well-structured report.
Include an introduction, main findings, and conclusion. Keep it concise (200-300 words)."""),
            HumanMessage(content=f"Topic: {state['topic']}\n\nResearch Notes:\n{all_notes}\n\nWrite the report:")
        ]

        response = invoke_with_retry(self.writer_llm, messages)

        new_state = dict(state)
        new_state['draft'] = response.content
        new_state['final_report'] = response.content

        return new_state

    def _route_from_coordinator(self, state: ResearchState) -> str:
        """Route based on coordinator's decision"""

        if state['iteration'] >= state['max_iterations']:
            return "end"

        step = state['current_step']

        if step == "research":
            return "researcher"
        elif step == "write":
            return "writer"
        else:
            return "end"

    def run(self, topic: str, max_iterations: int = 5) -> dict:
        """Run the research workflow"""

        initial_state: ResearchState = {
            "topic": topic,
            "research_notes": [],
            "draft": "",
            "final_report": "",
            "current_step": "start",
            "iteration": 0,
            "max_iterations": max_iterations
        }

        start_time = time.time()

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        end_time = time.time()

        return {
            "topic": topic,
            "final_report": final_state.get("final_report", ""),
            "research_notes": final_state.get("research_notes", []),
            "iterations": final_state.get("iteration", 0),
            "elapsed_ms": (end_time - start_time) * 1000
        }


# =============================================================================
# Main
# =============================================================================

def main():
    """Run the LangGraph research team"""

    print("=" * 60)
    print("  LANGGRAPH RESEARCH TEAM")
    print("=" * 60)

    # Create team
    team = ResearchTeam()

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
