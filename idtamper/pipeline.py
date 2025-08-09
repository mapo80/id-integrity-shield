
import json, os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
import numpy as np

from .aggregate import DEFAULT_WEIGHTS, fuse_scores
from .visualize import save_heatmap_gray, fuse_heatmaps, overlay_on_image
from .checks import ela, jpegghost, exif as exifcheck, noise, blockiness, copymove, splicing, trufor, noiseprintpp, mantranet

@dataclass
class AnalyzerConfig:
    weights: Optional[Dict[str,float]] = None
    threshold: float = 0.30
    check_params: Optional[Dict[str,Any]] = None
    check_thresholds: Optional[Dict[str,float]] = None

def _run_check(fn, name, pil_img, params):
    try:
        res = fn(pil_img, params=params.get(name) if params else None)
        score = res.get("score", None)
        hm = res.get("map", None)
        meta = res.get("meta", {})
        return {"name": name if res.get('name') is None else res.get('name'), "score": score, "map": hm, "meta": meta}
    except Exception as e:
        return {"name": name, "score": None, "map": None, "meta": {"error": str(e)}}

def analyze_image(image_path: str, out_dir: str, cfg: AnalyzerConfig):
    outp = Path(out_dir); outp.mkdir(parents=True, exist_ok=True)
    pil_img = Image.open(image_path).convert("RGB")
    # save a copy of original for reports
    try:
        import shutil
        shutil.copy2(image_path, str(outp/Path(image_path).name))
    except Exception:
        pass

    # run checks (explicit names so params/thresholds match keys)
    results = []
    for name, fn in [('trufor', trufor.run),
                     ('mantranet', mantranet.run),
                     ('noiseprintpp', noiseprintpp.run),
                     ('deep_onnx'.run),
                     ('ela95', ela.run),
                     ('jpeg_ghosts', jpegghost.run),
                     ('noise_inconsistency', noise.run),
                     ('splicing', splicing.run),
                     ('copy_move', copymove.run),
                     ('jpeg_blockiness', blockiness.run),
                     ('exif', exifcheck.run)]:
        results.append(_run_check(fn, name, pil_img, cfg.check_params or {}))

    # per_check dict with thresholds
    per_check = {}
    thr = cfg.check_thresholds or {}
    for r in results:
        nm = r["name"]
        per_check[nm] = {
            "score": r["score"],
            "threshold": float(thr.get(nm, 0.5)),
            "flag": (r["score"] is not None and float(r["score"]) >= float(thr.get(nm, 0.5))),
            "details": r.get("meta", {})
        }

    weights = cfg.weights or DEFAULT_WEIGHTS
    tamper_score = fuse_scores(per_check, weights)
    is_tampered = bool(tamper_score >= cfg.threshold)

    # Save heatmaps per-check
    artifacts = {}
    hm_maps = {}
    for r in results:
        if r.get("map") is not None:
            hm_name = f"heatmap_{r['name']}.png"
            save_heatmap_gray(r["map"], str(outp/hm_name))
            artifacts[hm_name[:-4]] = hm_name
            hm_maps[r["name"]] = r["map"]

    # fused + overlay
    fused = fuse_heatmaps(hm_maps, weights=weights)
    if fused is not None:
        save_heatmap_gray(fused, str(outp/"fused_heatmap.png"))
        ov = overlay_on_image(pil_img, fused, alpha=0.45)
        ov.save(str(outp/"overlay.png"))
        artifacts["fused_heatmap"] = "fused_heatmap.png"
        artifacts["overlay"] = "overlay.png"

    # --- Confidence computation (margin + overlap + agreement) ---
    import numpy as _np, math as _math
    strong_checks = ['trufor','noiseprintpp','copy_move','splicing','noise_inconsistency']
    mask_thr = float((cfg.check_params or {}).get('confidence_mask_thr', 0.6))
    tau = float((cfg.check_params or {}).get('confidence_tau', 0.10))
    alpha = float((cfg.check_params or {}).get('confidence_alpha', 0.30))
    beta  = float((cfg.check_params or {}).get('confidence_beta', 0.20))


    # Select flagged strong checks with a heatmap (resize to common size)
    sel_maps = []
    Ht, Wt = pil_img.size[1], pil_img.size[0]
    from PIL import Image as _Image
    for nm in strong_checks:
        pc = per_check.get(nm)
        if pc and pc.get('flag') and (nm in hm_maps):
            m = hm_maps[nm]
            a = np.asarray(m, dtype=float)
            if a.shape != (Ht, Wt):
                img = _Image.fromarray((np.clip(a,0,1)*255).astype('uint8'))
                img = img.resize((Wt, Ht), _Image.BILINEAR)
                a = np.asarray(img, dtype=float)/255.0
            sel_maps.append(a)

    # Overlap ratio = |intersection(h>thr)| / |union(h>thr)| over selected maps
    overlap_ratio = 0.0
    if len(sel_maps) >= 2:
        masks = [(m > mask_thr).astype(_np.uint8) for m in sel_maps]
        inter = masks[0].copy()
        union = masks[0].copy()
        for k in range(1, len(masks)):
            inter = (inter & masks[k])
            union = (union | masks[k])
        iu = float(inter.sum())
        uu = float(union.sum())
        overlap_ratio = (iu / uu) if uu > 0 else 0.0

    checks_forti_flag = sum(1 for nm in strong_checks if per_check.get(nm,{}).get('flag'))
    nstrong = len(strong_checks)

    margin = float(tamper_score - cfg.threshold)
    sig = 1.0 / (1.0 + _math.exp(-(margin / max(1e-6, tau))))
    confidence = sig * (1.0 + alpha * overlap_ratio) * (1.0 + beta * (checks_forti_flag / max(1, nstrong)))
    confidence = float(max(0.0, min(1.0, confidence)))

    report = {
        "image": os.path.basename(image_path),
        "tamper_score": tamper_score,
        "threshold": cfg.threshold,
        "is_tampered": is_tampered,
        "confidence": confidence,
        "confidence_components": {
            "margin": margin,
            "overlap_ratio": overlap_ratio,
            "checks_forti_flag": checks_forti_flag,
            "nstrong": nstrong,
            "tau": tau,
            "alpha": alpha,
            "beta": beta,
            "mask_thr": mask_thr
        },
        "per_check": per_check,
        "artifacts": artifacts
    }
    (outp/"report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report
