"""
Metrics Collection for Benchmarks

Collects system and task-level metrics during benchmark execution.
"""

import time
import threading
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os


@dataclass
class TaskMetrics:
    """Metrics for a single task execution"""
    task_name: str
    iteration: int
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    error: Optional[str] = None

    # Resource usage at start/end
    cpu_percent_start: float = 0.0
    cpu_percent_end: float = 0.0
    memory_used_start: int = 0
    memory_used_end: int = 0

    # Task-specific metrics
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemSnapshot:
    """Snapshot of system metrics at a point in time"""
    timestamp: float
    cpu_percent: float
    cpu_per_core: List[float]
    memory_total: int
    memory_used: int
    memory_percent: float
    disk_read_bytes: int
    disk_write_bytes: int
    net_bytes_sent: int
    net_bytes_recv: int


@dataclass
class BenchmarkResults:
    """Complete benchmark results"""
    benchmark_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    runner_type: str = "unknown"  # "native" or "clove"

    # Per-task results
    task_results: Dict[str, List[TaskMetrics]] = field(default_factory=dict)

    # System metrics over time
    system_snapshots: List[SystemSnapshot] = field(default_factory=list)

    # Aggregated statistics
    statistics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def add_task_metric(self, metric: TaskMetrics):
        """Add a task metric to results"""
        if metric.task_name not in self.task_results:
            self.task_results[metric.task_name] = []
        self.task_results[metric.task_name].append(metric)

    def compute_statistics(self):
        """Compute aggregate statistics for all tasks"""
        for task_name, metrics in self.task_results.items():
            durations = [m.duration_ms for m in metrics if m.success]
            if not durations:
                continue

            self.statistics[task_name] = {
                "count": len(metrics),
                "success_count": len(durations),
                "failure_count": len(metrics) - len(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
                "mean_ms": statistics.mean(durations),
                "median_ms": statistics.median(durations),
                "stddev_ms": statistics.stdev(durations) if len(durations) > 1 else 0,
                "p95_ms": self._percentile(durations, 95),
                "p99_ms": self._percentile(durations, 99),
                "throughput_per_sec": len(durations) / (sum(durations) / 1000) if sum(durations) > 0 else 0,
            }

    def _percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for JSON serialization"""
        return {
            "benchmark_name": self.benchmark_name,
            "runner_type": self.runner_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "statistics": self.statistics,
            "task_results": {
                name: [
                    {
                        "iteration": m.iteration,
                        "duration_ms": m.duration_ms,
                        "success": m.success,
                        "error": m.error,
                        "extra": m.extra,
                    }
                    for m in metrics
                ]
                for name, metrics in self.task_results.items()
            },
            "system_snapshots": [
                {
                    "timestamp": s.timestamp,
                    "cpu_percent": s.cpu_percent,
                    "memory_percent": s.memory_percent,
                }
                for s in self.system_snapshots
            ],
        }

    def save(self, output_dir: str):
        """Save results to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{self.benchmark_name}_{self.runner_type}_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        return filepath


class MetricsCollector:
    """Collects metrics during benchmark execution"""

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self._snapshots: List[SystemSnapshot] = []
        self._collecting = False
        self._thread: Optional[threading.Thread] = None
        self._clove_client = None

    def start_collection(self, use_clove: bool = False):
        """Start collecting system metrics in background"""
        self._collecting = True
        self._snapshots = []

        if use_clove:
            try:
                import sys
                sys.path.insert(0, 'agents/python_sdk')
                from clove_sdk import CloveClient
                self._clove_client = CloveClient()
                self._clove_client.connect()
            except Exception as e:
                print(f"Warning: Could not connect to Clove for metrics: {e}")
                self._clove_client = None

        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

    def stop_collection(self) -> List[SystemSnapshot]:
        """Stop collecting and return snapshots"""
        self._collecting = False
        if self._thread:
            self._thread.join(timeout=2)

        if self._clove_client:
            self._clove_client.disconnect()
            self._clove_client = None

        return self._snapshots

    def _collect_loop(self):
        """Background collection loop"""
        while self._collecting:
            try:
                snapshot = self._collect_snapshot()
                if snapshot:
                    self._snapshots.append(snapshot)
            except Exception as e:
                pass  # Ignore collection errors
            time.sleep(self.interval)

    def _collect_snapshot(self) -> Optional[SystemSnapshot]:
        """Collect a single system snapshot"""
        if self._clove_client:
            return self._collect_from_clove()
        else:
            return self._collect_from_proc()

    def _collect_from_clove(self) -> Optional[SystemSnapshot]:
        """Collect metrics via Clove kernel"""
        try:
            result = self._clove_client.get_system_metrics()
            if not result.get("success"):
                return None

            metrics = result.get("metrics", {})
            cpu = metrics.get("cpu", {})
            mem = metrics.get("memory", {})
            disk = metrics.get("disk", {})
            net = metrics.get("network", {})

            return SystemSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu.get("percent", 0),
                cpu_per_core=cpu.get("per_core", []),
                memory_total=mem.get("total", 0),
                memory_used=mem.get("used", 0),
                memory_percent=mem.get("percent", 0),
                disk_read_bytes=disk.get("read_bytes", 0),
                disk_write_bytes=disk.get("write_bytes", 0),
                net_bytes_sent=net.get("bytes_sent", 0),
                net_bytes_recv=net.get("bytes_recv", 0),
            )
        except Exception:
            return None

    def _collect_from_proc(self) -> Optional[SystemSnapshot]:
        """Collect metrics directly from /proc (fallback)"""
        try:
            # Read CPU stats
            cpu_percent = 0.0
            cpu_per_core = []
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if line.startswith('cpu '):
                        parts = line.split()[1:]
                        total = sum(int(p) for p in parts)
                        idle = int(parts[3])
                        cpu_percent = 100.0 * (1 - idle / total) if total > 0 else 0

            # Read memory stats
            mem_total = 0
            mem_available = 0
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_total = int(line.split()[1]) * 1024
                    elif line.startswith('MemAvailable:'):
                        mem_available = int(line.split()[1]) * 1024

            mem_used = mem_total - mem_available
            mem_percent = 100.0 * mem_used / mem_total if mem_total > 0 else 0

            return SystemSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                cpu_per_core=cpu_per_core,
                memory_total=mem_total,
                memory_used=mem_used,
                memory_percent=mem_percent,
                disk_read_bytes=0,
                disk_write_bytes=0,
                net_bytes_sent=0,
                net_bytes_recv=0,
            )
        except Exception:
            return None


class TaskTimer:
    """Context manager for timing task execution"""

    def __init__(self, task_name: str, iteration: int):
        self.task_name = task_name
        self.iteration = iteration
        self.start_time = 0.0
        self.end_time = 0.0
        self.success = True
        self.error: Optional[str] = None
        self.extra: Dict[str, Any] = {}

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        if exc_type is not None:
            self.success = False
            self.error = str(exc_val)
        return False  # Don't suppress exceptions

    def to_metric(self) -> TaskMetrics:
        """Convert to TaskMetrics"""
        return TaskMetrics(
            task_name=self.task_name,
            iteration=self.iteration,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=(self.end_time - self.start_time) * 1000,
            success=self.success,
            error=self.error,
            extra=self.extra,
        )
