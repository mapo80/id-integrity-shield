#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from idtamper.pipeline import analyze_image, AnalyzerConfig
from idtamper.profiles import load_profile

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("-o","--out", default="out")
    ap.add_argument("--profile", default="recapture-id")
    ap.add_argument("--weights", default=None)
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--check-thresholds", default=None)
    ap.add_argument("--params", default=None)
    args = ap.parse_args()

    prof = load_profile(args.profile)
    weights = prof.get("weights", {})
    thr = prof.get("threshold", 0.5)
    cthr = prof.get("thresholds", {})
    params = prof.get("params", {})

    if args.weights: weights = json.loads(Path(args.weights).read_text())
    if args.threshold is not None: thr = float(args.threshold)
    if args.check_thresholds: cthr = json.loads(Path(args.check_thresholds).read_text())
    if args.params: params = json.loads(Path(args.params).read_text())

    cfg = AnalyzerConfig(weights=weights, threshold=thr, check_params=params, check_thresholds=cthr)
    rep = analyze_image(args.image, args.out, cfg)
    print(json.dumps(rep, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()