#!/usr/bin/env python3
import argparse, json, os, csv
from pathlib import Path
from idtamper.pipeline import analyze_image, AnalyzerConfig
from idtamper.profiles import load_profile

IMG_EXTS = {'.jpg','.jpeg','.png','.bmp','.tif','.tiff','.webp'}

def infer_label(path: Path):
    parts = [p.lower() for p in path.parts]
    if any(p in ('fake','tampered','spliced','splice','forged','forg') for p in parts): return 'tampered'
    if any(p in ('real','authentic','genuine','original') for p in parts): return 'genuine'
    return ''

def main():
    ap = argparse.ArgumentParser(description="Scan dataset folder and produce report")
    ap.add_argument("--input","-i", required=True)
    ap.add_argument("--out","-o", default="runs/dataset")
    ap.add_argument("--profile", default="recapture-id")
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--weights", default=None)
    ap.add_argument("--check-thresholds", default=None)
    ap.add_argument("--params", default=None)
    ap.add_argument("--save-artifacts", action="store_true")
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
    in_root = Path(args.input); out_root = Path(args.out); out_root.mkdir(parents=True, exist_ok=True)

    rows = []
    for p in in_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            rel = p.relative_to(in_root)
            out_dir = out_root/"items"/rel.parent/p.stem if args.save_artifacts else out_root/"items"
            out_dir.mkdir(parents=True, exist_ok=True)
            rep = analyze_image(str(p), str(out_dir), cfg)
            rows.append({
                "path": str(rel),
                "label": infer_label(rel),
                "pred": "tampered" if rep["is_tampered"] else "genuine",
                "score": rep["tamper_score"],
                **{f"{k}_score": v["score"] for k,v in rep["per_check"].items()},
                **{f"{k}_thr": v["threshold"] for k,v in rep["per_check"].items()},
                **{f"{k}_flag": v["flag"] for k,v in rep["per_check"].items()},
            })

    # CSV
    if rows:
        cols = list(rows[0].keys())
        with (out_root/"dataset_report.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
            for r in rows: w.writerow(r)

    # Summary
    tot = {"n":0,"tp":0,"tn":0,"fp":0,"fn":0}
    for r in rows:
        if r["label"]:
            tot["n"] += 1
            if r["label"]=="tampered" and r["pred"]=="tampered": tot["tp"] += 1
            elif r["label"]=="genuine" and r["pred"]=="genuine": tot["tn"] += 1
            elif r["label"]=="genuine" and r["pred"]=="tampered": tot["fp"] += 1
            elif r["label"]=="tampered" and r["pred"]=="genuine": tot["fn"] += 1
    prec = tot["tp"]/max(1,(tot["tp"]+tot["fp"]))
    rec  = tot["tp"]/max(1,(tot["tp"]+tot["fn"]))
    acc  = (tot["tp"]+tot["tn"])/max(1, tot["n"])
    f1   = 2*prec*rec/max(1e-9,(prec+rec)) if (prec+rec)>0 else 0.0

    summary = {"count": len(rows), "confusion": tot, "precision": prec, "recall": rec, "accuracy": acc, "f1": f1,
               "threshold": thr, "weights": weights}
    (out_root/"summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"csv": str(out_root/'dataset_report.csv'), "summary": str(out_root/'summary.json')}, indent=2))

if __name__ == "__main__":
    main()