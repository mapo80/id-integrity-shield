from typing import Any, Dict, List, Optional

from . import pipeline

__all__ = ["analyze", "analyze_batch"]


def analyze(
    image_path: str,
    profile: str,
    params: Optional[Dict[str, Any]] = None,
    parallel_config: Optional[pipeline.ParallelConfig] = None,
):
    return pipeline.analyze_image(
        image_path=image_path,
        profile=profile,
        params=params or {},
        parallel_config=parallel_config,
    )


def analyze_batch(
    image_paths: List[str],
    profile: str,
    params: Optional[Dict[str, Any]] = None,
    parallel_config: Optional[pipeline.ParallelConfig] = None,
):
    return [
        pipeline.analyze_image(
            image_path=p,
            profile=profile,
            params=params or {},
            parallel_config=parallel_config,
        )
        for p in image_paths
    ]
