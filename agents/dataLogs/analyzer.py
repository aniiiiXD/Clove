#!/usr/bin/env python3
"""
AgentOS Log Analyzer - View historical logs and generate graphs

Usage:
    python3 analyzer.py                    # List available logs
    python3 analyzer.py <logfile>          # Analyze specific log
    python3 analyzer.py <logfile> --graph  # Show ASCII graphs
    python3 analyzer.py <logfile> --export # Export to CSV
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class LogAnalyzer:
    def __init__(self, log_file):
        self.log_file = Path(log_file)
        self.entries = []
        self.load()

    def load(self):
        if not self.log_file.exists():
            print(f"Error: Log file not found: {self.log_file}")
            sys.exit(1)

        with open(self.log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        if not self.entries:
            print("Error: No valid entries in log file")
            sys.exit(1)

    def summary(self):
        print(f"\n{'='*60}")
        print(f" Log Analysis: {self.log_file.name}")
        print(f"{'='*60}\n")

        first = self.entries[0]
        last = self.entries[-1]

        start_time = datetime.fromisoformat(first["timestamp"])
        end_time = datetime.fromisoformat(last["timestamp"])
        duration = end_time - start_time

        print(f"Duration:     {duration}")
        print(f"Entries:      {len(self.entries)}")
        print(f"Start:        {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End:          {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Stats summary
        max_agents = max(e["stats"]["total_agents"] for e in self.entries)
        max_running = max(e["stats"]["running"] for e in self.entries)
        total_failed = sum(e["stats"]["failed"] for e in self.entries)

        print(f"\nPeak agents:  {max_agents}")
        print(f"Peak running: {max_running}")
        print(f"Total fails:  {total_failed}")

        # Unique agents seen
        agent_names = set()
        for entry in self.entries:
            for agent in entry.get("agents", []):
                agent_names.add(agent.get("name", "unknown"))

        print(f"\nUnique agents seen ({len(agent_names)}):")
        for name in sorted(agent_names):
            print(f"  - {name}")

    def graph(self):
        print(f"\n{'='*60}")
        print(" Running Agents Over Time")
        print(f"{'='*60}\n")

        values = [e["stats"]["running"] for e in self.entries]
        self._ascii_graph(values, height=12)

        print(f"\n{'='*60}")
        print(" Total Agents Over Time")
        print(f"{'='*60}\n")

        values = [e["stats"]["total_agents"] for e in self.entries]
        self._ascii_graph(values, height=12)

    def _ascii_graph(self, values, height=10, width=60):
        if not values:
            return

        # Downsample if too many points
        if len(values) > width:
            step = len(values) / width
            sampled = []
            for i in range(width):
                idx = int(i * step)
                sampled.append(values[idx])
            values = sampled

        max_val = max(max(values), 1)
        min_val = min(values)

        # Y-axis labels
        for row in range(height):
            threshold = max_val - (max_val - min_val) * row / (height - 1)
            label = f"{int(threshold):>4} │"
            line = ""
            for val in values:
                normalized = (val - min_val) / (max_val - min_val) if max_val != min_val else 0
                bar_height = int(normalized * (height - 1))
                if (height - 1 - row) <= bar_height:
                    line += "█"
                else:
                    line += " "
            print(f"{label}{line}")

        # X-axis
        print(f"     └{'─' * len(values)}")
        print(f"      0{' ' * (len(values) - 6)}→ time")

    def export_csv(self):
        csv_file = self.log_file.with_suffix(".csv")

        with open(csv_file, "w") as f:
            # Header
            f.write("timestamp,total_agents,running,stopped,failed\n")

            # Data
            for entry in self.entries:
                ts = entry["timestamp"]
                stats = entry["stats"]
                f.write(f"{ts},{stats['total_agents']},{stats['running']},{stats['stopped']},{stats['failed']}\n")

        print(f"Exported to: {csv_file}")

    def agent_timeline(self):
        print(f"\n{'='*60}")
        print(" Agent Timeline")
        print(f"{'='*60}\n")

        # Track agent appearances
        agent_first_seen = {}
        agent_last_seen = {}
        agent_states = defaultdict(list)

        for entry in self.entries:
            ts = entry["timestamp"]
            for agent in entry.get("agents", []):
                name = agent.get("name", "unknown")
                state = agent.get("state", "UNKNOWN")

                if name not in agent_first_seen:
                    agent_first_seen[name] = ts
                agent_last_seen[name] = ts
                agent_states[name].append(state)

        # Print timeline
        for name in sorted(agent_first_seen.keys()):
            first = datetime.fromisoformat(agent_first_seen[name])
            last = datetime.fromisoformat(agent_last_seen[name])
            duration = last - first
            states = agent_states[name]
            final_state = states[-1]

            state_icon = "●" if final_state == "RUNNING" else "○" if final_state == "STOPPED" else "✗"
            print(f"  {state_icon} {name:<25} {duration}")


def list_logs():
    log_dir = Path(__file__).parent / "logs"
    if not log_dir.exists():
        print("No logs directory found. Run monitor.py with --log first.")
        return

    logs = sorted(log_dir.glob("*.jsonl"), reverse=True)
    if not logs:
        print("No log files found.")
        return

    print("\nAvailable logs:")
    print("-" * 60)
    for log in logs:
        size = log.stat().st_size
        size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
        print(f"  {log.name:<40} {size_str:>10}")
    print(f"\nUsage: python3 analyzer.py logs/<filename>")


def main():
    parser = argparse.ArgumentParser(description="AgentOS Log Analyzer")
    parser.add_argument("logfile", nargs="?", help="Log file to analyze")
    parser.add_argument("--graph", action="store_true", help="Show ASCII graphs")
    parser.add_argument("--export", action="store_true", help="Export to CSV")
    parser.add_argument("--timeline", action="store_true", help="Show agent timeline")
    args = parser.parse_args()

    if not args.logfile:
        list_logs()
        return

    analyzer = LogAnalyzer(args.logfile)
    analyzer.summary()

    if args.graph:
        analyzer.graph()

    if args.timeline:
        analyzer.agent_timeline()

    if args.export:
        analyzer.export_csv()


if __name__ == "__main__":
    main()
