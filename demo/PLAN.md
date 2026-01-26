# DrugDiscovery Demo: Before & After Clove

## Concept

A multi-agent pharmaceutical research system that:
1. Researches drug candidates for a target disease
2. Runs computational tests/simulations
3. Analyzes and validates results
4. Generates a final research report

**Sales Pitch:** Show the same system built two ways - traditional Python (fragile) vs Clove (robust) - demonstrating why OS-level isolation matters for production AI agents.

---

## The Agents

| Agent | Role | Resource Profile |
|-------|------|------------------|
| **Coordinator** | Orchestrates workflow, assigns tasks | Low CPU/memory |
| **Researcher** | Searches literature, finds drug candidates via LLM | LLM-heavy |
| **Simulator** | Runs molecular property calculations | High CPU/memory |
| **Validator** | Cross-checks results, flags anomalies | LLM-heavy |
| **Reporter** | Compiles final report | Low resources |

---

## Part 1: WITHOUT Clove (The Problem)

### Architecture
```
┌─────────────────────────────────────────────────────┐
│              Single Python Process                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Coordinator │  │ Researcher  │  │ Simulator   │ │
│  │  (thread)   │  │  (thread)   │  │  (thread)   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│  ┌─────────────┐  ┌─────────────┐                   │
│  │ Validator   │  │  Reporter   │   SHARED STATE   │
│  │  (thread)   │  │  (thread)   │   (race conds)   │
│  └─────────────┘  └─────────────┘                   │
└─────────────────────────────────────────────────────┘
         │
         ▼ One crash = ALL DEAD
```

### Implementation: `without_clove/`

```
without_clove/
├── main.py                 # Entry point - runs all agents as threads
├── agents/
│   ├── __init__.py
│   ├── coordinator.py      # Orchestration logic
│   ├── researcher.py       # LLM-based research
│   ├── simulator.py        # Computational tests (with memory leak!)
│   ├── validator.py        # Result validation
│   └── reporter.py         # Report generation
├── shared_state.py         # Global mutable state (bad pattern)
├── llm_client.py           # Direct Gemini API calls (no queuing)
└── requirements.txt        # google-genai
```

### Failure Scenarios to Demonstrate

1. **Crash Cascade** - Simulator raises exception → entire process dies
2. **Memory Leak** - Simulator accumulates data → OOMs everything
3. **LLM Race Condition** - Multiple agents hit rate limits
4. **Runaway Agent** - Infinite loop can't be stopped
5. **No Observability** - No audit trail, printf debugging only

---

## Part 2: WITH Clove (The Solution)

### Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        Clove Kernel                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Process Supervisor + LLM Queue + IPC Router + Audit Log  │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
┌────┴────┐          ┌────┴────┐          ┌────┴────┐
│Researcher│          │Simulator│          │Validator│
│ PID 1001 │          │ PID 1002│          │ PID 1003│
│ 256MB max│          │ 512MB   │          │ 256MB   │
└─────────┘          └─────────┘          └─────────┘
     │                     │                     │
     └─────────── IPC (kernel-mediated) ─────────┘
```

### Implementation: `with_clove/`

```
with_clove/
├── main.py                 # Spawns agents via Clove SDK
├── agents/
│   ├── __init__.py
│   ├── coordinator.py      # Uses client.spawn(), client.send()
│   ├── researcher.py       # Uses client.think() - fair queued
│   ├── simulator.py        # Memory-limited, can crash safely
│   ├── validator.py        # Uses client.think()
│   └── reporter.py         # Reads results via IPC
└── requirements.txt        # clove-sdk
```

### How Clove Solves Each Problem

| Problem | Without Clove | With Clove |
|---------|---------------|------------|
| Crash cascade | All agents die | Only crashed agent dies |
| Memory leak | OOMs everything | Killed at limit, auto-restarted |
| LLM race | Rate limit errors | Fair queuing through kernel |
| Runaway agent | Can't stop it | `pause()` or `kill()` |
| No observability | printf debugging | Metrics TUI, audit logs |

---

## Drug Discovery Workflow

```
User: "Find treatments for Type 2 Diabetes"
                    │
                    ▼
            ┌───────────────┐
            │  COORDINATOR  │
            │  Orchestrates │
            └───────┬───────┘
                    │
        ┌───────────┼───────────┐
        ▼           │           │
┌───────────────┐   │           │
│  RESEARCHER   │   │           │
│ Find 5 drug   │   │           │
│ candidates    │   │           │
└───────┬───────┘   │           │
        │           │           │
        ▼           ▼           │
        ┌───────────────┐       │
        │   SIMULATOR   │       │
        │ Test each     │       │
        │ candidate     │       │
        │ (CRASH HERE!) │       │
        └───────┬───────┘       │
                │               │
                ▼               ▼
        ┌───────────────┐
        │   VALIDATOR   │
        │ Verify results│
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │   REPORTER    │
        │ Generate PDF  │
        └───────────────┘
```

---

## Files to Create

```
demo/
├── PLAN.md                      # This file
├── README.md                    # Overview, setup, run instructions
├── without_clove/
│   ├── main.py                  # Entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── coordinator.py       # Thread-based orchestration
│   │   ├── researcher.py        # LLM research (direct API)
│   │   ├── simulator.py         # Has memory leak + crash
│   │   ├── validator.py         # Validation logic
│   │   └── reporter.py          # Report generation
│   ├── shared_state.py          # Global dict (race conditions)
│   ├── llm_client.py            # Direct Gemini wrapper
│   └── requirements.txt
├── with_clove/
│   ├── main.py                  # Spawns via CloveClient
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── coordinator.py       # Uses spawn(), send()
│   │   ├── researcher.py        # Uses think()
│   │   ├── simulator.py         # Same crash, but isolated
│   │   ├── validator.py         # Uses think()
│   │   └── reporter.py          # Uses recv(), fetch()
│   └── requirements.txt
└── comparison.md                # Side-by-side for sales deck
```

---

## Implementation Plan

### Phase 1: Without Clove (~10 files)
1. Create directory structure
2. `llm_client.py` - Gemini API wrapper
3. `shared_state.py` - Global mutable dict
4. `agents/researcher.py` - Find drug candidates via LLM
5. `agents/simulator.py` - Molecular tests WITH intentional memory leak + crash
6. `agents/validator.py` - Cross-check results
7. `agents/reporter.py` - Generate summary
8. `agents/coordinator.py` - Spawn threads, manage workflow
9. `main.py` - Entry point
10. `requirements.txt`

### Phase 2: With Clove (~10 files)
1. Create directory structure
2. Convert each agent to use CloveClient
3. Replace threading with spawn()
4. Replace shared_state with store()/fetch()
5. Replace direct LLM with think()
6. Replace queues with send()/recv()
7. Keep same intentional failures
8. `main.py` - Spawn all agents
9. `requirements.txt`

### Phase 3: Documentation
1. `demo/README.md` - Setup and run instructions
2. `demo/comparison.md` - Sales comparison table

---

## Key Code Patterns

### Without Clove (Fragile)
```python
# shared_state.py - Race condition prone
results = {}  # Global mutable state

# simulator.py - Memory leak
accumulated_data = []  # Never cleared
def simulate(molecule):
    accumulated_data.append(heavy_computation())  # LEAK!
    if random.random() < 0.3:
        raise Exception("Simulation failed!")  # CRASH!

# main.py - All threads share fate
threads = [Thread(target=agent.run) for agent in agents]
for t in threads:
    t.start()
# One crash = all dead
```

### With Clove (Robust)
```python
# main.py - Isolated processes
with CloveClient() as client:
    client.spawn(name="simulator", script="agents/simulator.py",
                 limits={"memory": 512*1024*1024},
                 restart_policy="on-failure")

# simulator.py - Same crash, but isolated
with CloveClient() as client:
    client.register_name("simulator")
    while True:
        msg = client.recv_messages()
        result = simulate(msg["molecule"])  # Can crash safely!
        client.send_message(result, to_name="validator")
```

---

## Demo Script

### Run Without Clove
```bash
cd demo/without_clove
pip install -r requirements.txt
python main.py --disease "Type 2 Diabetes"

# Expected output:
# [00:00] Coordinator: Starting research...
# [00:05] Researcher: Found 5 candidates
# [00:10] Simulator: Testing metformin...
# [00:15] Simulator: Testing glipizide...
# [00:20] ERROR: Simulation crashed!
# [00:20] Process terminated. All progress lost.
```

### Run With Clove
```bash
# Terminal 1: Kernel
sudo ./build/clove_kernel

# Terminal 2: Metrics TUI
python agents/dashboard/metrics_tui.py

# Terminal 3: Demo
cd demo/with_clove
python main.py --disease "Type 2 Diabetes"

# Expected output:
# [00:00] Coordinator: Starting research...
# [00:05] Researcher: Found 5 candidates
# [00:10] Simulator: Testing metformin...
# [00:15] Simulator: Testing glipizide...
# [00:20] Simulator CRASHED - auto-restarting (attempt 1)
# [00:22] Simulator: Resumed, testing sitagliptin...
# [00:30] Validator: All results verified
# [00:35] Reporter: Report saved to output/report.md
# [00:35] SUCCESS: Research complete!
```

---

## Verification

1. **Without Clove crashes correctly:**
   ```bash
   python demo/without_clove/main.py
   # Should crash and lose all progress
   ```

2. **With Clove recovers:**
   ```bash
   python demo/with_clove/main.py
   # Should recover from crash and complete
   ```

3. **Metrics visible in TUI:**
   - See each agent's memory usage
   - Watch simulator restart
   - View audit log

4. **Pause/Resume works:**
   ```python
   client.pause(name="simulator")  # Freezes agent
   client.resume(name="simulator") # Resumes
   ```

---

## Sales Talking Points

### For Engineers
- Process isolation via Linux namespaces
- cgroups v2 memory/CPU limits
- Fair LLM queuing (no rate limit races)
- Full audit trail of every syscall

### For Managers
- Agents can't crash each other
- Auto-recovery with exponential backoff
- Real-time observability dashboard
- Compliance-ready audit logging

### Demo Highlights
1. Show crash in without_clove → everything dies
2. Show same crash in with_clove → only simulator dies
3. Show auto-restart in TUI metrics
4. Show audit log of what happened
5. Show pause/resume control

---

## Timeline Estimate

| Phase | Task | Files |
|-------|------|-------|
| Phase 1 | Without Clove implementation | ~10 files |
| Phase 2 | With Clove conversion | ~10 files |
| Phase 3 | Documentation & polish | ~3 files |
| **Total** | | ~23 files |
