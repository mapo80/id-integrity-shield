import json
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

from .aggregate import DEFAULT_WEIGHTS, fuse_scores
from .checks import (
    blockiness,
    copymove,
    ela,
    exif as exifcheck,
    jpegghost,
    mantranet,
    noise,
    noiseprintpp,
    splicing,
)
from .execution import ParallelConfig, init_onnx_session_opts, apply_thread_env
from .metrics import measure, embed_report_metrics, describe_runtime
from .preproc import PreprocOptions, build_preproc_cache
from .visualize import fuse_heatmaps, overlay_on_image, save_heatmap_gray

import concurrent.futures as cf
import onnxruntime as ort
import cv2

# cache for ONNX sessions inside worker processes
_ORT_SESS: Dict[str, Any] = {}


@dataclass
class AnalyzerConfig:
    weights: Optional[Dict[str, float]] = None
    threshold: float = 0.30
    check_params: Optional[Dict[str, Any]] = None
    check_thresholds: Optional[Dict[str, float]] = None


def _run_check(fn, name, inp, params, sessions):
    p = dict(params.get(name, {})) if params else {}
    if sessions and name in sessions and sessions[name] is not None:
        p.setdefault("session", sessions[name])
    try:
        res = fn(inp, params=p)
        score = res.get("score", None)
        hm = res.get("map", None)
        meta = res.get("meta", {})
        return {"name": res.get("name", name), "score": score, "map": hm, "meta": meta}
    except Exception as e:  # pragma: no cover - defensive
        return {"name": name, "score": None, "map": None, "meta": {"error": str(e)}}


def _resolve_model_paths(cfg: AnalyzerConfig) -> Dict[str, str]:
    res = {}
    p = cfg.check_params or {}
    for k in ("mantranet", "noiseprintpp"):
        mp = p.get(k, {}).get("model_path") if isinstance(p.get(k), dict) else None
        if mp:
            res[k] = mp
    return res


def _worker_init(cfg: ParallelConfig, model_paths: Dict[str, str]):
    with apply_thread_env(cfg):
        try:
            cv2.setNumThreads(1)
        except Exception:
            pass
        so = init_onnx_session_opts(cfg)
        for name, pth in model_paths.items():
            try:
                sess = ort.InferenceSession(pth, sess_options=so, providers=["CPUExecutionProvider"])
                # warm-up with dummy input
                inp = sess.get_inputs()[0]
                shape = [d if isinstance(d, int) else 1 for d in inp.shape]
                dummy = np.zeros(shape, dtype=np.float32)
                sess.run(None, {inp.name: dummy})
                _ORT_SESS[name] = sess
            except Exception:
                _ORT_SESS[name] = None


def _analyze_single(image_path: str, out_dir: str, cfg: AnalyzerConfig, pcfg: ParallelConfig, sessions: Dict[str, Any] | None = None):
    sessions = sessions or _ORT_SESS
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)
    pil_img = Image.open(image_path).convert("RGB")

    try:  # save copy of original
        import shutil

        shutil.copy2(image_path, str(outp / Path(image_path).name))
    except Exception:
        pass

    cache = build_preproc_cache(np.asarray(pil_img), PreprocOptions())

    results: List[Dict[str, Any]] = []
    metrics = []

    deep_checks = [
        ("mantranet", mantranet.run, pil_img),
        ("noiseprintpp", noiseprintpp.run, pil_img),
    ]
    signal_checks = [
        ("ela95", ela.run, cache),
        ("jpeg_ghosts", jpegghost.run, cache),
        ("noise_inconsistency", noise.run, cache),
        ("splicing", splicing.run, cache),
        ("copy_move", copymove.run, cache),
        ("jpeg_blockiness", blockiness.run, cache),
        ("exif", exifcheck.run, pil_img),
    ]

    # Deep checks sequential
    for name, fn, inp in deep_checks:
        res, metr = measure(lambda fn=fn, name=name, inp=inp: _run_check(fn, name, inp, cfg.check_params or {}, sessions), name)
        results.append(res)
        metrics.append(metr)

    def _do(item):
        name, fn, inp = item
        return measure(lambda fn=fn, name=name, inp=inp: _run_check(fn, name, inp, cfg.check_params or {}, sessions), name)

    if pcfg.parallel_signal_checks and len(signal_checks) > 1:
        with cf.ThreadPoolExecutor() as tp:
            for res, metr in tp.map(_do, signal_checks):
                results.append(res)
                metrics.append(metr)
    else:
        for item in signal_checks:
            res, metr = _do(item)
            results.append(res)
            metrics.append(metr)

    # per_check dict with thresholds
    per_check = {}
    thr = cfg.check_thresholds or {}
    for r in results:
        nm = r["name"]
        per_check[nm] = {
            "score": r["score"],
            "threshold": float(thr.get(nm, 0.5)),
            "flag": (r["score"] is not None and float(r["score"]) >= float(thr.get(nm, 0.5))),
            "details": r.get("meta", {}),
        }

    weights = cfg.weights or DEFAULT_WEIGHTS
    tamper_score = fuse_scores(per_check, weights)
    is_tampered = bool(tamper_score >= cfg.threshold)

    # Save heatmaps per-check
    artifacts: Dict[str, str] = {}
    hm_maps = {}
    for r in results:
        if r.get("map") is not None:
            hm_name = f"heatmap_{r['name']}.png"
            save_heatmap_gray(r["map"], str(outp / hm_name))
            artifacts[hm_name[:-4]] = hm_name
            hm_maps[r["name"]] = r["map"]

    # fused + overlay
    fused = fuse_heatmaps(hm_maps, weights=weights)
    if fused is not None:
        save_heatmap_gray(fused, str(outp / "fused_heatmap.png"))
        ov = overlay_on_image(pil_img, fused, alpha=0.45)
        ov.save(str(outp / "overlay.png"))
        artifacts["fused_heatmap"] = "fused_heatmap.png"
        artifacts["overlay"] = "overlay.png"

    # --- Confidence computation (margin + overlap + agreement) ---
    import numpy as _np, math as _math

    strong_checks = ['noiseprintpp', 'copy_move', 'splicing', 'noise_inconsistency']
    mask_thr = float((cfg.check_params or {}).get('confidence_mask_thr', 0.6))
    tau = float((cfg.check_params or {}).get('confidence_tau', 0.10))
    alpha = float((cfg.check_params or {}).get('confidence_alpha', 0.30))
    beta = float((cfg.check_params or {}).get('confidence_beta', 0.20))

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
                img = _Image.fromarray((np.clip(a, 0, 1) * 255).astype('uint8'))
                img = img.resize((Wt, Ht), _Image.BILINEAR)
                a = np.asarray(img, dtype=float) / 255.0
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

    checks_forti_flag = sum(1 for nm in strong_checks if per_check.get(nm, {}).get('flag'))
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
            "mask_thr": mask_thr,
        },
        "per_check": per_check,
        "artifacts": artifacts,
    }

    total_ms = sum(m.ms for m in metrics)
    report = embed_report_metrics(report, total_ms, metrics, describe_runtime(pcfg))

    (outp / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def analyze_images(image_paths: List[str], out_dir: str, cfg: AnalyzerConfig, parallel: ParallelConfig = ParallelConfig()) -> List[Dict[str, Any]]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    if parallel.max_parallel_images <= 1:
        return [
            _analyze_single(path, str(out_root / Path(path).stem), cfg, parallel, _ORT_SESS)
            for path in image_paths
        ]

    model_paths = _resolve_model_paths(cfg)
    with cf.ProcessPoolExecutor(
        max_workers=parallel.max_parallel_images,
        initializer=_worker_init,
        initargs=(parallel, model_paths),
    ) as ex:
        futures = [
            ex.submit(_analyze_single, path, str(out_root / Path(path).stem), cfg, parallel, None)
            for path in image_paths
        ]
        return [f.result() for f in futures]


def analyze_image(image_path: str, out_dir: str, cfg: AnalyzerConfig, parallel: ParallelConfig = ParallelConfig()):
    # For backward compatibility we store artifacts directly in ``out_dir``.
    if parallel.max_parallel_images <= 1:
        return _analyze_single(image_path, out_dir, cfg, parallel, _ORT_SESS)
    # if parallelism requested, fall back to batch API
    return analyze_images([image_path], out_dir, cfg, parallel)[0]
