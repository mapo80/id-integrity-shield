from __future__ import annotations

"""Simple structures for recording timing and resource usage metrics."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Iterable
import time
import psutil


@dataclass
class Timing:
    start: float
    end: float

    @property
    def ms(self) -> float:
        return (self.end - self.start) * 1000.0


@dataclass
class CheckMetrics:
    name: str
    ms: float
    cpu_percent: float
    rss_bytes: int


def measure(fn, name: str):
    """Measure execution time and resource usage of ``fn``.

    Parameters
    ----------
    fn:
        Callable with no arguments.
    name:
        Name of the check being measured.
    """

    proc = psutil.Process()
    cpu_before = proc.cpu_percent(interval=None)
    rss_before = proc.memory_info().rss
    start = time.perf_counter()
    result = fn()
    end = time.perf_counter()
    cpu_after = proc.cpu_percent(interval=None)
    rss_after = proc.memory_info().rss
    metrics = CheckMetrics(
        name=name,
        ms=(end - start) * 1000.0,
        cpu_percent=max(0.0, cpu_after - cpu_before),
        rss_bytes=max(0, rss_after - rss_before),
    )
    return result, metrics


class Stopwatch:
    def __init__(self):
        self.start = time.perf_counter()

    def stop(self) -> Timing:
        end = time.perf_counter()
        return Timing(self.start, end)


def describe_runtime(cfg) -> Dict[str, Any]:
    return {
        "parallel_config": cfg.__dict__,
        "hw": {"cpu_count": psutil.cpu_count(), "ram_gb": psutil.virtual_memory().total / 1e9},
    }


def embed_report_metrics(report: Dict[str, Any], total_ms: float, checks: Iterable[CheckMetrics], runtime: Dict[str, Any]):
    report["metrics"] = {
        "total_ms": total_ms,
        "checks": [c.__dict__ for c in checks],
    }
    report["metrics"].update(runtime)
    return report
