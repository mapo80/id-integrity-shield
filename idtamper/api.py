"""Public convenience API for running the pipeline."""

from __future__ import annotations

from typing import List, Optional

from .pipeline import analyze_image, analyze_images, AnalyzerConfig
from .execution import ParallelConfig

__all__ = ["analyze", "analyze_batch"]


def analyze(
    image_path: str,
    profile: Optional[AnalyzerConfig] = None,
    *,
    out_dir: str = "out",
    parallel_config: Optional[ParallelConfig] = None,
):
    """Analyze a single image using the high-level convenience API."""
    cfg = profile or AnalyzerConfig()
    pc = parallel_config or ParallelConfig()
    return analyze_image(image_path, out_dir, cfg, pc)


def analyze_batch(
    image_paths: List[str],
    profile: Optional[AnalyzerConfig] = None,
    *,
    out_dir: str = "out",
    parallel_config: Optional[ParallelConfig] = None,
):
    """Analyze multiple images efficiently (leverages per-image parallelism in the pipeline)."""
    cfg = profile or AnalyzerConfig()
    pc = parallel_config or ParallelConfig()
    return analyze_images(image_paths, out_dir, cfg, pc)
