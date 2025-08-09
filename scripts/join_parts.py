#!/usr/bin/env python3
import argparse
from pathlib import Path
def main():
    ap = argparse.ArgumentParser(description="Join split ONNX parts into a single .onnx file")
    ap.add_argument("--parts", nargs="+", required=True, help="List of part files in order")
    ap.add_argument("--out", required=True, help="Output .onnx path")
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fo:
        for p in args.parts:
            with open(p, "rb") as fi:
                fo.write(fi.read())
    print(f"Wrote: {out} ({out.stat().st_size} bytes)")
if __name__ == "__main__":
    main()