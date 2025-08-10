from __future__ import annotations

"""Execution utilities for controlling parallelism and thread usage."""

from dataclasses import dataclass
import contextlib
import os
from typing import Dict, Iterator

import onnxruntime as ort


@dataclass
class ParallelConfig:
    """Configuration for parallel execution.

    Attributes
    ----------
    max_parallel_images:
        Maximum number of images to process in parallel at the pipeline level.
    parallel_signal_checks:
        Whether to parallelise classic signal based checks for a single image
        using a thread pool.
    onnx_intra_threads:
        Number of intra-op threads used by ONNX Runtime sessions.
    onnx_inter_threads:
        Number of inter-op threads used by ONNX Runtime sessions.
    env_thread_caps:
        If ``True`` set environment thread related variables such as
        ``OMP_NUM_THREADS`` to avoid oversubscription.
    """

    max_parallel_images: int = 1
    parallel_signal_checks: bool = True
    onnx_intra_threads: int = 1
    onnx_inter_threads: int = 1
    env_thread_caps: bool = True


_THREAD_VARS = [
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
]


@contextlib.contextmanager
def apply_thread_env(config: ParallelConfig) -> Iterator[None]:
    """Context manager to set/restore environment thread variables."""

    old: Dict[str, str] = {}
    if config.env_thread_caps:
        for v in _THREAD_VARS:
            old[v] = os.environ.get(v, "")
            os.environ[v] = str(config.onnx_intra_threads)
    try:
        yield
    finally:
        if config.env_thread_caps:
            for v, val in old.items():
                if val:
                    os.environ[v] = val
                else:
                    os.environ.pop(v, None)


def init_onnx_session_opts(config: ParallelConfig) -> ort.SessionOptions:
    """Create ONNX Runtime ``SessionOptions`` according to the configuration."""

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = int(config.onnx_intra_threads)
    opts.inter_op_num_threads = int(config.onnx_inter_threads)
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    return opts
