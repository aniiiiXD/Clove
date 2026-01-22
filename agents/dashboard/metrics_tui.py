#!/usr/bin/env python3
"""
Clove Metrics TUI - Terminal Dashboard for Clove Kernel

A real-time terminal UI showing:
- System metrics (CPU, memory, disk, network)
- Active agents with resource usage
- Kernel status and uptime

Usage:
    python3 metrics_tui.py

Requirements:
    pip install rich
"""

import os
import sys
import time
import signal
from datetime import datetime, timedelta

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.style import Style
from rich import box
from rich.align import Align

try:
    from clove import CloveClient
except ImportError:
    print("Error: Could not import CloveClient. Make sure the SDK is in path.")
    sys.exit(1)


# ============================================================================
# Styling
# ============================================================================

COLORS = {
    "primary": "cyan",
    "secondary": "blue",
    "success": "green",
    "warning": "yellow",
    "danger": "red",
    "muted": "dim white",
    "accent": "magenta",
}

LOGO = """
 ██████╗██╗      ██████╗ ██╗   ██╗███████╗
██╔════╝██║     ██╔═══██╗██║   ██║██╔════╝
██║     ██║     ██║   ██║██║   ██║█████╗
██║     ██║     ██║   ██║╚██╗ ██╔╝██╔══╝
╚██████╗███████╗╚██████╔╝ ╚████╔╝ ███████╗
 ╚═════╝╚══════╝ ╚═════╝   ╚═══╝  ╚══════╝
"""

MINI_LOGO = "◆ CLOVE"


# ============================================================================
# Helpers
# ============================================================================

def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


def format_duration(ms: int) -> str:
    """Format milliseconds to human readable duration"""
    seconds = ms // 1000
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def get_cpu_bar(percent: float, width: int = 20) -> Text:
    """Create a colored CPU usage bar"""
    filled = int(percent / 100 * width)
    empty = width - filled

    if percent < 50:
        color = COLORS["success"]
    elif percent < 80:
        color = COLORS["warning"]
    else:
        color = COLORS["danger"]

    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style=COLORS["muted"])
    bar.append(f" {percent:5.1f}%", style=color)
    return bar


def get_memory_bar(used: int, total: int, width: int = 20) -> Text:
    """Create a colored memory usage bar"""
    if total == 0:
        return Text("N/A", style=COLORS["muted"])

    percent = (used / total) * 100
    filled = int(percent / 100 * width)
    empty = width - filled

    if percent < 60:
        color = COLORS["success"]
    elif percent < 85:
        color = COLORS["warning"]
    else:
        color = COLORS["danger"]

    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style=COLORS["muted"])
    bar.append(f" {format_bytes(used)}/{format_bytes(total)}", style=color)
    return bar


# ============================================================================
# Dashboard Components
# ============================================================================

class MetricsDashboard:
    """Main dashboard class"""

    def __init__(self):
        self.console = Console()
        self.client = None
        self.connected = False
        self.start_time = datetime.now()
        self.last_update = None
        self.error_message = None

        # Cached data
        self.system_metrics = {}
        self.agents = []
        self.agent_count = 0

    def connect(self) -> bool:
        """Connect to kernel"""
        try:
            self.client = CloveClient()
            if self.client.connect():
                self.connected = True
                return True
        except Exception as e:
            self.error_message = str(e)
        return False

    def disconnect(self):
        """Disconnect from kernel"""
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass
        self.connected = False

    def refresh_data(self):
        """Fetch fresh data from kernel"""
        if not self.connected:
            return

        try:
            # Get system metrics
            result = self.client.get_system_metrics()
            if result and result.get("success"):
                self.system_metrics = result.get("metrics", {})

            # Get agent metrics
            result = self.client.get_all_agent_metrics()
            if result and result.get("success"):
                self.agents = result.get("agents", [])
                self.agent_count = result.get("count", 0)

            self.last_update = datetime.now()
            self.error_message = None

        except Exception as e:
            self.error_message = str(e)
            self.connected = False

    def make_header(self) -> Panel:
        """Create header panel"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=2)
        grid.add_column(justify="right", ratio=1)

        # Status indicator
        if self.connected:
            status = Text("● CONNECTED", style=f"bold {COLORS['success']}")
        else:
            status = Text("● DISCONNECTED", style=f"bold {COLORS['danger']}")

        # Title
        title = Text(MINI_LOGO, style=f"bold {COLORS['primary']}")
        title.append(" Metrics Dashboard", style="bold white")

        # Time
        now = datetime.now().strftime("%H:%M:%S")
        uptime = datetime.now() - self.start_time
        time_text = Text(f"⏱ {now}", style=COLORS["muted"])

        grid.add_row(status, title, time_text)

        return Panel(grid, box=box.ROUNDED, style=COLORS["primary"])

    def make_system_panel(self) -> Panel:
        """Create system metrics panel"""
        cpu = self.system_metrics.get("cpu", {})
        memory = self.system_metrics.get("memory", {})
        disk = self.system_metrics.get("disk", {})
        network = self.system_metrics.get("network", {})

        table = Table(box=None, show_header=False, expand=True, padding=(0, 1))
        table.add_column("Label", style="bold", width=12)
        table.add_column("Value", ratio=1)

        # CPU
        cpu_percent = cpu.get("percent", 0)
        table.add_row("CPU", get_cpu_bar(cpu_percent))

        # Load average
        load = cpu.get("load_avg", [0, 0, 0])
        load_text = Text(f"{load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}", style=COLORS["secondary"])
        load_text.append("  (1m/5m/15m)", style=COLORS["muted"])
        table.add_row("Load", load_text)

        # Memory
        mem_used = memory.get("used", 0)
        mem_total = memory.get("total", 1)
        table.add_row("Memory", get_memory_bar(mem_used, mem_total))

        # Disk I/O
        disk_read = disk.get("read_bytes", 0)
        disk_write = disk.get("write_bytes", 0)
        disk_text = Text()
        disk_text.append(f"R: {format_bytes(disk_read)}", style=COLORS["success"])
        disk_text.append(" | ", style=COLORS["muted"])
        disk_text.append(f"W: {format_bytes(disk_write)}", style=COLORS["warning"])
        table.add_row("Disk I/O", disk_text)

        # Network
        net_recv = network.get("bytes_recv", 0)
        net_sent = network.get("bytes_sent", 0)
        net_text = Text()
        net_text.append(f"↓ {format_bytes(net_recv)}", style=COLORS["success"])
        net_text.append(" | ", style=COLORS["muted"])
        net_text.append(f"↑ {format_bytes(net_sent)}", style=COLORS["accent"])
        table.add_row("Network", net_text)

        return Panel(
            table,
            title="[bold]System Metrics[/bold]",
            title_align="left",
            box=box.ROUNDED,
            border_style=COLORS["secondary"]
        )

    def make_agents_panel(self) -> Panel:
        """Create agents panel"""
        if not self.agents:
            content = Align.center(
                Text("No active agents", style=COLORS["muted"]),
                vertical="middle"
            )
            return Panel(
                content,
                title=f"[bold]Agents ({self.agent_count})[/bold]",
                title_align="left",
                box=box.ROUNDED,
                border_style=COLORS["accent"],
                height=12
            )

        table = Table(box=box.SIMPLE, expand=True, show_edge=False)
        table.add_column("ID", style="dim", width=4)
        table.add_column("Name", style="bold", width=20)
        table.add_column("Status", width=10)
        table.add_column("CPU", width=8)
        table.add_column("Memory", width=12)
        table.add_column("Uptime", width=10)

        for agent in self.agents[:10]:  # Show max 10 agents
            agent_id = str(agent.get("agent_id", "?"))
            name = agent.get("name", "unknown")[:18]
            status = agent.get("status", "unknown")
            uptime = format_duration(agent.get("uptime_ms", 0))

            # Status styling
            if status == "running":
                status_text = Text("● running", style=COLORS["success"])
            elif status == "stopped":
                status_text = Text("○ stopped", style=COLORS["muted"])
            else:
                status_text = Text(f"? {status}", style=COLORS["warning"])

            # Process metrics
            process = agent.get("process", {})
            cpu_pct = process.get("cpu", {}).get("percent", 0)
            mem_rss = process.get("memory", {}).get("rss", 0)

            cpu_text = Text(f"{cpu_pct:.1f}%", style=COLORS["secondary"])
            mem_text = Text(format_bytes(mem_rss), style=COLORS["secondary"])

            table.add_row(agent_id, name, status_text, cpu_text, mem_text, uptime)

        if len(self.agents) > 10:
            table.add_row("", f"... and {len(self.agents) - 10} more", "", "", "", "")

        return Panel(
            table,
            title=f"[bold]Agents ({self.agent_count})[/bold]",
            title_align="left",
            box=box.ROUNDED,
            border_style=COLORS["accent"]
        )

    def make_footer(self) -> Panel:
        """Create footer panel"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right", ratio=1)

        # Last update
        if self.last_update:
            update_text = Text(f"Updated: {self.last_update.strftime('%H:%M:%S')}", style=COLORS["muted"])
        else:
            update_text = Text("Not updated", style=COLORS["muted"])

        # Controls
        controls = Text("[q] Quit  [r] Refresh", style=COLORS["muted"])

        # Error
        if self.error_message:
            error_text = Text(f"Error: {self.error_message[:40]}", style=COLORS["danger"])
        else:
            error_text = Text("")

        grid.add_row(update_text, controls, error_text)

        return Panel(grid, box=box.ROUNDED, style=COLORS["muted"], height=3)

    def make_layout(self) -> Layout:
        """Create the dashboard layout"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )

        layout["main"].split_row(
            Layout(name="system", ratio=1),
            Layout(name="agents", ratio=1)
        )

        layout["header"].update(self.make_header())
        layout["system"].update(self.make_system_panel())
        layout["agents"].update(self.make_agents_panel())
        layout["footer"].update(self.make_footer())

        return layout

    def make_splash(self) -> Panel:
        """Create splash screen while connecting"""
        content = Text()
        content.append(LOGO, style=f"bold {COLORS['primary']}")
        content.append("\n\n")
        content.append("Connecting to kernel...", style=COLORS["muted"])

        return Panel(
            Align.center(content, vertical="middle"),
            box=box.DOUBLE,
            border_style=COLORS["primary"]
        )

    def make_error_screen(self) -> Panel:
        """Create error screen when not connected"""
        content = Text()
        content.append(LOGO, style=f"bold {COLORS['danger']}")
        content.append("\n\n")
        content.append("Failed to connect to Clove kernel\n\n", style=f"bold {COLORS['danger']}")
        content.append("Make sure the kernel is running:\n", style=COLORS["muted"])
        content.append("  ./build/clove_kernel\n\n", style=COLORS["secondary"])
        if self.error_message:
            content.append(f"Error: {self.error_message}\n\n", style=COLORS["warning"])
        content.append("Press [q] to quit, [r] to retry", style=COLORS["muted"])

        return Panel(
            Align.center(content, vertical="middle"),
            box=box.DOUBLE,
            border_style=COLORS["danger"]
        )

    def run(self):
        """Run the dashboard"""
        # Show splash and connect
        with Live(self.make_splash(), console=self.console, refresh_per_second=4) as live:
            time.sleep(0.5)
            connected = self.connect()

            if not connected:
                live.update(self.make_error_screen())
                # Wait for quit or retry
                import select
                import tty
                import termios

                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setcbreak(sys.stdin.fileno())
                    while True:
                        if select.select([sys.stdin], [], [], 0.5)[0]:
                            key = sys.stdin.read(1).lower()
                            if key == 'q':
                                return
                            elif key == 'r':
                                live.update(self.make_splash())
                                time.sleep(0.3)
                                if self.connect():
                                    break
                                live.update(self.make_error_screen())
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        # Main loop
        import select
        import tty
        import termios

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())

            with Live(self.make_layout(), console=self.console, refresh_per_second=2) as live:
                last_refresh = 0

                while True:
                    # Check for input
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()
                        if key == 'q':
                            break
                        elif key == 'r':
                            self.refresh_data()
                            live.update(self.make_layout())

                    # Auto refresh every 2 seconds
                    now = time.time()
                    if now - last_refresh >= 2:
                        self.refresh_data()

                        if self.connected:
                            live.update(self.make_layout())
                        else:
                            live.update(self.make_error_screen())

                        last_refresh = now

        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.disconnect()
            self.console.print("\n[dim]Goodbye![/dim]")


# ============================================================================
# Main
# ============================================================================

def main():
    """Entry point"""
    dashboard = MetricsDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
