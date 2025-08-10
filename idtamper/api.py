"""Public convenience API for running the pipeline."""

from typing import Optional, Dict, Any, List

from .pipeline import analyze_image, analyze_images, AnalyzerConfig
from .execution import ParallelConfig

__all__ = ["analyze", "analyze_batch"]


def analyze(image_path: str, profile: AnalyzerConfig | None = None, *, out_dir: str = "out", parallel_config: Optional[ParallelConfig] = None):
    cfg = profile or AnalyzerConfig()
    pc = parallel_config or ParallelConfig()
    return analyze_image(image_path, out_dir, cfg, pc)


def analyze_batch(image_paths: List[str], profile: AnalyzerConfig | None = None, *, out_dir: str = "out", parallel_config: Optional[ParallelConfig] = None):
    cfg = profile or AnalyzerConfig()
    pc = parallel_config or ParallelConfig()
    return analyze_images(image_paths, out_dir, cfg, pc)
