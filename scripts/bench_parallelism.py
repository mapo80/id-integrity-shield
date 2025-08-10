#!/usr/bin/env python3
"""Benchmark serial vs parallel execution of the forensic pipeline."""
import argparse
import json
import os
import statistics
import time
from pathlib import Path

import numpy as np

from idtamper.pipeline import AnalyzerConfig, analyze_images
from idtamper.execution import ParallelConfig
from idtamper.metrics import describe_runtime


def run(dataset: Path, cfg: AnalyzerConfig, pcfg: ParallelConfig, runs: int):
    imgs = [str(p) for p in sorted(dataset.glob("*")) if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    if not imgs:
        raise SystemExit("no images found in dataset")
    latencies = []
    t_all_start = time.perf_counter()
    for _ in range(runs):
        t0 = time.perf_counter()
        analyze_images(imgs, "_bench_out", cfg, pcfg)
        latencies.append((time.perf_counter() - t0) * 1000.0 / len(imgs))
    total = time.perf_counter() - t_all_start
    imgs_per_s = (len(imgs) * runs) / total
    median_ms = statistics.median(latencies)
    p95_ms = float(np.percentile(latencies, 95)) if len(latencies) > 1 else latencies[0]
    return {
        "images_per_s": imgs_per_s,
        "median_ms_per_img": median_ms,
        "p95_ms_per_img": p95_ms,
        "runtime": describe_runtime(pcfg),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, type=Path, help="directory with images")
    ap.add_argument("--profile", default=None, help="profile name (unused placeholder)")
    ap.add_argument("--runs", type=int, default=1)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--serial", action="store_true")
    mode.add_argument("--parallel", action="store_true")
    args = ap.parse_args()

    cfg = AnalyzerConfig()
    if args.serial:
        pcfg = ParallelConfig(
            max_parallel_images=1,
            parallel_signal_checks=False,
            onnx_intra_threads=os.cpu_count() or 1,
            onnx_inter_threads=1,
        )
        out_name = "bench_serial.json"
    else:
        pcfg = ParallelConfig(max_parallel_images=2, parallel_signal_checks=True)
        out_name = "bench_parallel.json"

    res = run(args.dataset, cfg, pcfg, args.runs)
    Path(out_name).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
