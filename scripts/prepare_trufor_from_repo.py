#!/usr/bin/env python3
import argparse, glob, os
from pathlib import Path
from join_parts import main as join_main  # reuse join_parts

def main():
    ap = argparse.ArgumentParser(description="Assemble TruFor ONNX from split parts in a repo checkout")
    ap.add_argument("--repo", required=True, help="Path to mapo80/TruFor repo checkout")
    ap.add_argument("--model", choices=["480","384"], default="480", help="Which TruFor model to assemble")
    ap.add_argument("--out", required=True, help="Output .onnx path")
    args = ap.parse_args()

    repo = Path(args.repo); assert repo.exists(), f"Repo not found: {repo}"
    onnx_dir = repo/"onnx_models"
    if args.model == "480":
        prefix = "trufor_480x480_op13.onnx.part"
    else:
        prefix = "trufor_384x384_op13.onnx.part"
    parts = sorted(str(p) for p in onnx_dir.glob(prefix + "*"))
    if not parts:
        raise SystemExit(f"No parts found at {onnx_dir} with prefix {prefix}*")
    # call join_parts
    os.system(f"python {Path(__file__).parent/'join_parts.py'} --out {args.out} --parts " + " ".join(parts))

if __name__ == "__main__":
    main()