"""JPEG ghost detection with optional preprocessing cache."""

from __future__ import annotations

import io
import numpy as np
from PIL import Image

from ..preproc import PreprocCache


def run(img_or_cache, params=None):
    """Execute JPEG ghost detection."""

    p = params or {}
    qualities = p.get("qualities", [75, 85, 95])
    tp = float(p.get("top_percent", 5.0))

    if isinstance(img_or_cache, PreprocCache):
        pil_image = Image.fromarray(img_or_cache.img)
    else:
        pil_image = img_or_cache

    a = np.asarray(pil_image, dtype=np.int16)
    acc = None
    for q in qualities:
        buf = io.BytesIO()
        pil_image.save(buf, "JPEG", quality=int(q))
        rec = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
        b = np.asarray(rec, dtype=np.int16)
        diff = np.abs(a - b).astype(np.float32).mean(axis=2)
        acc = diff if acc is None else np.maximum(acc, diff)

    hm = (acc - acc.min()) / (acc.max() - acc.min() + 1e-8)
    thr = np.percentile(acc, 100.0 - tp)
    top = acc[acc >= thr]
    score = float((top.mean() / 255.0) if top.size else 0.0)

    return {
        "name": "jpeg_ghosts",
        "score": score,
        "map": hm,
        "meta": {"qualities": qualities, "top_percent": tp},
    }

