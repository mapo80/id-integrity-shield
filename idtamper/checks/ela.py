"""Error Level Analysis check with optional preprocessing cache."""

from __future__ import annotations

import io
import numpy as np
from PIL import Image

from ..preproc import PreprocCache


def run(img_or_cache, params=None):
    """Execute the ELA check."""

    p = params or {}
    q = int(p.get("quality", 95))
    scale = float(p.get("scale", 10.0))
    tp = float(p.get("top_percent", 5.0))

    if isinstance(img_or_cache, PreprocCache):
        pil_image = Image.fromarray(img_or_cache.img_orig)
    else:
        pil_image = img_or_cache

    buf = io.BytesIO()
    pil_image.save(buf, "JPEG", quality=q)
    rec = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    a = np.asarray(pil_image, dtype=np.int16)
    b = np.asarray(rec, dtype=np.int16)
    diff = np.abs(a - b).astype(np.float32)
    gray = diff.mean(axis=2)
    s = scale / max(1.0, gray.mean())
    gray = np.clip(gray * s, 0, 255)
    hm = (gray - gray.min()) / (gray.max() - gray.min() + 1e-8)
    thr = np.percentile(gray, 100.0 - tp)
    top = gray[gray >= thr]
    score = float((top.mean() / 255.0) if top.size else 0.0)
    meta = {"quality": q, "scale": scale, "top_percent": tp}
    return {"name": "ela95", "score": score, "map": hm, "meta": meta}

