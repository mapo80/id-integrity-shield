from __future__ import annotations

"""Simple structures for recording timing and resource usage metrics."""

from dataclasses import dataclass
from typing import Optional
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
