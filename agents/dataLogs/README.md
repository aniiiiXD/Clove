# AgentOS Monitor & Logs

htop-style terminal interface for monitoring AgentOS agents with optional logging and graphs.

## Quick Start

```bash
# Make sure kernel is running
./build/agentos_kernel

# Basic monitor (htop-style)
python3 agents/dataLogs/monitor.py

# With logging enabled
python3 agents/dataLogs/monitor.py --log

# With live graphs
python3 agents/dataLogs/monitor.py --graph

# Both logging and graphs
python3 agents/dataLogs/monitor.py --log --graph
```

## Monitor Interface

```
═══════════════════ AgentOS Monitor ════════════════════
Status: CONNECTED  │  Uptime: 0:05:23  │  LOGGING

Agents: 3  │  Running: 2  │  Stopped: 0  │  Failed: 1

  ID  NAME                  PID      STATE       UPTIME
   1  orchestrator        12345    RUNNING     5m 23s
   2  worker-1            12346    RUNNING     4m 12s
   3  worker-2            12347    FAILED      2m 45s

────────────────────────────────────────────────────────
 Q:Quit  K:Kill  R:Refresh  ↑↓:Select      Log: agent_log_xxx.jsonl
```

## Controls

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `K` | Kill selected agent |
| `R` | Force refresh |
| `↑/↓` | Select agent |

## Logging (Optional)

Enable with `--log` flag. Logs are saved to `agents/dataLogs/logs/`.

Log format (JSONL):
```json
{"timestamp": "2026-01-20T10:30:00", "stats": {...}, "agents": [...]}
```

## Analyzing Logs

```bash
# List available logs
python3 agents/dataLogs/analyzer.py

# Analyze a log file
python3 agents/dataLogs/analyzer.py logs/agent_log_20260120_103000.jsonl

# Show ASCII graphs
python3 agents/dataLogs/analyzer.py logs/agent_log_xxx.jsonl --graph

# Show agent timeline
python3 agents/dataLogs/analyzer.py logs/agent_log_xxx.jsonl --timeline

# Export to CSV
python3 agents/dataLogs/analyzer.py logs/agent_log_xxx.jsonl --export
```

## Graph Example (--graph flag)

```
Running Agents Over Time
════════════════════════

  10 │                    ████████
   8 │               █████████████████
   6 │          ██████████████████████████
   4 │     █████████████████████████████████
   2 │ ████████████████████████████████████████
   0 │█████████████████████████████████████████████
     └─────────────────────────────────────────────
      0                                      → time
```

## Files

| File | Description |
|------|-------------|
| `monitor.py` | Live htop-style monitor |
| `analyzer.py` | Log analysis and graphs |
| `logs/` | Log files (created when using --log) |

## Data Tracked

- Total agents count
- Running/stopped/failed breakdown
- Per-agent: ID, name, PID, state, uptime
- Timestamps for all events

## Tips

1. Run with `--log` during demos to capture data
2. Use `--graph` to see real-time trends
3. Analyze logs later with `analyzer.py --graph`
4. Export to CSV for spreadsheet analysis
