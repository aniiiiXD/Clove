#!/usr/bin/env python3
"""
AgentOS Monitor - htop-style interface for agent monitoring

Usage:
    python3 monitor.py              # Live monitor
    python3 monitor.py --log        # Enable logging to file
    python3 monitor.py --log --graph # Enable logging with graphs
"""

import curses
import time
import json
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python_sdk"))
from clove_sdk import AgentOSClient


class AgentMonitor:
    def __init__(self, enable_logging=False, enable_graphs=False):
        self.client = None
        self.agents = []
        self.stats = {
            "total_agents": 0,
            "running": 0,
            "stopped": 0,
            "failed": 0,
            "total_llm_calls": 0,
            "total_tokens": 0,
        }
        self.history = []  # For graphs
        self.enable_logging = enable_logging
        self.enable_graphs = enable_graphs
        self.log_file = None
        self.start_time = datetime.now()
        self.selected_idx = 0
        self.scroll_offset = 0

        if enable_logging:
            log_dir = Path(__file__).parent / "logs"
            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = log_dir / f"agent_log_{timestamp}.jsonl"

    def connect(self):
        try:
            self.client = AgentOSClient()
            self.client.connect()
            return True
        except Exception:
            return False

    def disconnect(self):
        if self.client:
            self.client.disconnect()

    def refresh_data(self):
        if not self.client:
            return False
        try:
            result = self.client.list_agents()
            if isinstance(result, list):
                self.agents = result
            elif isinstance(result, dict) and "agents" in result:
                self.agents = result["agents"]
            else:
                self.agents = []

            # Update stats
            self.stats["total_agents"] = len(self.agents)
            self.stats["running"] = sum(1 for a in self.agents if a.get("state") == "RUNNING")
            self.stats["stopped"] = sum(1 for a in self.agents if a.get("state") == "STOPPED")
            self.stats["failed"] = sum(1 for a in self.agents if a.get("state") == "FAILED")

            # Record history for graphs
            if self.enable_graphs:
                self.history.append({
                    "time": datetime.now().isoformat(),
                    "running": self.stats["running"],
                    "total": self.stats["total_agents"],
                })
                # Keep last 60 data points
                if len(self.history) > 60:
                    self.history.pop(0)

            # Log if enabled
            if self.enable_logging and self.log_file:
                self._write_log()

            return True
        except Exception:
            return False

    def _write_log(self):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats.copy(),
            "agents": self.agents,
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def run(self, stdscr):
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(1000)  # Refresh every 1s

        # Colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # Running
        curses.init_pair(2, curses.COLOR_RED, -1)     # Failed
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Stopped
        curses.init_pair(4, curses.COLOR_CYAN, -1)    # Header
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Selected

        while True:
            try:
                stdscr.clear()
                height, width = stdscr.getmaxyx()

                # Refresh data
                connected = self.refresh_data()

                # Draw header
                self._draw_header(stdscr, width, connected)

                # Draw stats bar
                self._draw_stats(stdscr, width)

                # Draw agent list
                self._draw_agents(stdscr, height, width)

                # Draw footer
                self._draw_footer(stdscr, height, width)

                # Draw graph if enabled
                if self.enable_graphs and height > 20:
                    self._draw_graph(stdscr, height, width)

                stdscr.refresh()

                # Handle input
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == curses.KEY_UP and self.selected_idx > 0:
                    self.selected_idx -= 1
                elif key == curses.KEY_DOWN and self.selected_idx < len(self.agents) - 1:
                    self.selected_idx += 1
                elif key == ord('k') or key == ord('K'):
                    self._kill_selected()
                elif key == ord('r') or key == ord('R'):
                    self.refresh_data()

            except KeyboardInterrupt:
                break

    def _draw_header(self, stdscr, width, connected):
        title = " AgentOS Monitor "
        uptime = str(datetime.now() - self.start_time).split('.')[0]
        status = "CONNECTED" if connected else "DISCONNECTED"
        status_color = curses.color_pair(1) if connected else curses.color_pair(2)

        # Title bar
        stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(0, 0, "═" * width)
        stdscr.addstr(0, (width - len(title)) // 2, title)
        stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)

        # Status line
        stdscr.addstr(1, 2, f"Status: ")
        stdscr.attron(status_color | curses.A_BOLD)
        stdscr.addstr(status)
        stdscr.attroff(status_color | curses.A_BOLD)
        stdscr.addstr(f"  │  Uptime: {uptime}")

        if self.enable_logging:
            stdscr.addstr(f"  │  ")
            stdscr.attron(curses.color_pair(3))
            stdscr.addstr("LOGGING")
            stdscr.attroff(curses.color_pair(3))

    def _draw_stats(self, stdscr, width):
        y = 3
        stdscr.addstr(y, 2, "Agents: ")
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(f"{self.stats['total_agents']}")
        stdscr.attroff(curses.A_BOLD)

        stdscr.addstr("  │  Running: ")
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(f"{self.stats['running']}")
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        stdscr.addstr("  │  Stopped: ")
        stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        stdscr.addstr(f"{self.stats['stopped']}")
        stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

        stdscr.addstr("  │  Failed: ")
        stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(f"{self.stats['failed']}")
        stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)

    def _draw_agents(self, stdscr, height, width):
        y_start = 5
        max_rows = height - 10 if self.enable_graphs else height - 8

        # Header
        stdscr.attron(curses.A_REVERSE)
        header = f"{'ID':>4}  {'NAME':<20}  {'PID':>8}  {'STATE':<10}  {'UPTIME':<12}"
        stdscr.addstr(y_start, 2, header.ljust(width - 4))
        stdscr.attroff(curses.A_REVERSE)

        # Agents
        if not self.agents:
            stdscr.addstr(y_start + 2, 4, "No agents running")
            return

        for i, agent in enumerate(self.agents):
            if i >= max_rows:
                break

            y = y_start + 1 + i
            agent_id = agent.get("id", "?")
            name = agent.get("name", "unknown")[:20]
            pid = agent.get("pid", "?")
            state = agent.get("state", "UNKNOWN")
            uptime_ms = agent.get("uptime_ms", 0)
            uptime = self._format_uptime(uptime_ms)

            # State color
            if state == "RUNNING":
                state_color = curses.color_pair(1)
            elif state == "FAILED":
                state_color = curses.color_pair(2)
            else:
                state_color = curses.color_pair(3)

            # Row
            line = f"{agent_id:>4}  {name:<20}  {pid:>8}  "

            if i == self.selected_idx:
                stdscr.attron(curses.color_pair(5))
                stdscr.addstr(y, 2, line)
                stdscr.addstr(f"{state:<10}")
                stdscr.addstr(f"  {uptime:<12}")
                padding = width - 4 - len(line) - 10 - 14
                if padding > 0:
                    stdscr.addstr(" " * padding)
                stdscr.attroff(curses.color_pair(5))
            else:
                stdscr.addstr(y, 2, line)
                stdscr.attron(state_color)
                stdscr.addstr(f"{state:<10}")
                stdscr.attroff(state_color)
                stdscr.addstr(f"  {uptime:<12}")

    def _draw_footer(self, stdscr, height, width):
        y = height - 2
        stdscr.attron(curses.color_pair(4))
        stdscr.addstr(y, 0, "─" * width)
        stdscr.attroff(curses.color_pair(4))

        help_text = " Q:Quit  K:Kill  R:Refresh  ↑↓:Select "
        stdscr.addstr(y + 1, 2, help_text)

        if self.enable_logging and self.log_file:
            log_info = f"Log: {self.log_file.name}"
            stdscr.addstr(y + 1, width - len(log_info) - 2, log_info)

    def _draw_graph(self, stdscr, height, width):
        if len(self.history) < 2:
            return

        graph_height = 6
        graph_width = min(60, width - 10)
        y_start = height - 8 - graph_height
        x_start = 4

        stdscr.addstr(y_start, x_start, "Running Agents (last 60s):")

        # Get data
        values = [h["running"] for h in self.history[-graph_width:]]
        max_val = max(max(values), 1)

        # Draw graph
        for row in range(graph_height):
            threshold = max_val * (graph_height - row) / graph_height
            line = ""
            for val in values:
                if val >= threshold:
                    line += "█"
                elif val >= threshold - (max_val / graph_height / 2):
                    line += "▄"
                else:
                    line += " "
            stdscr.addstr(y_start + 1 + row, x_start, "│")
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(line)
            stdscr.attroff(curses.color_pair(1))

        # X axis
        stdscr.addstr(y_start + 1 + graph_height, x_start, "└" + "─" * len(values))

    def _format_uptime(self, ms):
        if ms < 1000:
            return f"{ms}ms"
        secs = ms // 1000
        if secs < 60:
            return f"{secs}s"
        mins = secs // 60
        secs = secs % 60
        if mins < 60:
            return f"{mins}m {secs}s"
        hours = mins // 60
        mins = mins % 60
        return f"{hours}h {mins}m"

    def _kill_selected(self):
        if not self.agents or self.selected_idx >= len(self.agents):
            return
        agent = self.agents[self.selected_idx]
        name = agent.get("name")
        if name and self.client:
            try:
                self.client.kill(name=name)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="AgentOS Monitor")
    parser.add_argument("--log", action="store_true", help="Enable logging to file")
    parser.add_argument("--graph", action="store_true", help="Show live graphs")
    args = parser.parse_args()

    monitor = AgentMonitor(enable_logging=args.log, enable_graphs=args.graph)

    if not monitor.connect():
        print("Error: Could not connect to AgentOS kernel")
        print("Make sure kernel is running: ./build/agentos_kernel")
        sys.exit(1)

    try:
        curses.wrapper(monitor.run)
    finally:
        monitor.disconnect()
        if args.log:
            print(f"\nLogs saved to: {monitor.log_file}")


if __name__ == "__main__":
    main()
