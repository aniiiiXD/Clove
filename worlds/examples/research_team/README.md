# Research Team - Multi-Agent Example

A multi-agent research team implemented in three ways:
1. **LangGraph** - StateGraph pattern
2. **Clove** - Single process, kernel-mediated
3. **Clove Multi-Process** - Real process isolation with IPC

## The System

Three agents collaborate to research a topic and produce a report:

```
┌─────────────┐     ┌────────────┐     ┌────────────┐
│ Coordinator │────▶│ Researcher │────▶│   Writer   │
│  (decides)  │◀────│ (gathers)  │◀────│(synthesizes│
└─────────────┘     └────────────┘     └────────────┘
```

- **Coordinator**: Decides next action (research/write/done)
- **Researcher**: Gathers facts and insights on the topic
- **Writer**: Synthesizes research into a final report

## Quick Start

```bash
# Make sure Clove kernel is running (for Clove benchmarks)
./build/clove_kernel &

# Run the benchmark
cd worlds/examples/research_team
python3 benchmark.py --iterations 3
```

## Files

| File | Description |
|------|-------------|
| `langgraph_version.py` | LangGraph StateGraph implementation |
| `clove_version.py` | Clove single-process implementation |
| `clove_multiprocess.py` | Clove with real spawned agent processes |
| `benchmark.py` | Comparison benchmark runner |

## Running Individual Versions

```bash
# LangGraph version
python3 langgraph_version.py

# Clove version (requires kernel)
python3 clove_version.py

# Clove multi-process version (requires kernel)
python3 clove_multiprocess.py
```

## Benchmark Options

```bash
python3 benchmark.py --help

Options:
  --iterations N      Iterations per framework (default: 3)
  --topic "..."       Research topic
  --langgraph-only    Only run LangGraph
  --clove-only        Only run Clove single-process
  --multiprocess-only Only run Clove multi-process
  --output DIR        Output directory for results
```

## Architecture Comparison

### LangGraph
```python
# StateGraph pattern - all in one process
workflow = StateGraph(ResearchState)
workflow.add_node("coordinator", coordinator_fn)
workflow.add_node("researcher", researcher_fn)
workflow.add_node("writer", writer_fn)
graph = workflow.compile()
result = graph.invoke(initial_state)
```

### Clove (Single Process)
```python
# Direct kernel LLM calls - minimal overhead
with CloveClient() as client:
    decision = client.think(coordinator_prompt)  # Kernel handles LLM
    notes = client.think(researcher_prompt)
    report = client.think(writer_prompt)
```

### Clove (Multi-Process)
```python
# Real process isolation - fault tolerant
client.spawn(name="researcher", script="researcher_agent.py")
client.spawn(name="writer", script="writer_agent.py")

# IPC messaging
client.send_message({"type": "research", "topic": topic}, to_name="researcher")
result = client.recv_messages(max_messages=10)
messages = result.get("messages", [])
```

## Key Differences

| Aspect | LangGraph | Clove Single | Clove Multi |
|--------|-----------|--------------|-------------|
| Process Model | Single | Single | Multiple |
| Fault Isolation | None | None | Full |
| LLM Calls | Direct API | Kernel-mediated | Kernel-mediated |
| Agent Communication | In-memory | N/A | IPC via kernel |
| Overhead | Framework + API | Kernel IPC | Kernel IPC + spawn |

## Why Clove Multi-Process Matters

1. **Crash Isolation**: If researcher crashes, writer continues
2. **Resource Limits**: Each agent can have memory/CPU limits
3. **Security**: Agents can be sandboxed (namespaces)
4. **Scalability**: Agents can run on different machines (via relay)

## Sample Output

```
========================================
  BENCHMARK COMPARISON
========================================

Framework            Mean (ms)    Min (ms)     Max (ms)     Errors
--------------------------------------------------------------------------------
langgraph            12500        11200        14100        0
clove                8200         7800         8900         0
clove_multiprocess   9100         8500         10200        0
--------------------------------------------------------------------------------

Winner: clove (8200ms mean)
  vs langgraph: 1.52x faster
  vs clove_multiprocess: 1.11x faster
```

## Prerequisites

- Python 3.10+
- Clove kernel running (`./build/clove_kernel`)
- Dependencies:
  ```bash
  pip install langgraph langchain-google-genai python-dotenv
  ```
- API key in `.env` file (GOOGLE_API_KEY or GEMINI_API_KEY)
