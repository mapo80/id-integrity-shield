"""Image preprocessing utilities and cache."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List
import io

import numpy as np
from PIL import Image


@dataclass
class PreprocOptions:
    max_side: int = 1600
    keep_exif: bool = False
    colorspace: str = "RGB"


@dataclass
class PreprocCache:
    img_orig: np.ndarray
    img_gray: np.ndarray
    img_ycbcr: np.ndarray
    pyramid: List[np.ndarray]
    jpeg_reenc_90: np.ndarray | None = None


def build_preproc_cache(image: np.ndarray, opts: PreprocOptions) -> PreprocCache:
    """Build a :class:`PreprocCache` from an RGB ``image`` array."""

    pil = Image.fromarray(image)
    W, H = pil.size
    if max(W, H) > opts.max_side:
        scale = opts.max_side / float(max(W, H))
        pil = pil.resize((int(W * scale), int(H * scale)), Image.BILINEAR)

    img_rgb = np.asarray(pil, dtype=np.uint8)
    img_gray = np.asarray(pil.convert("L"), dtype=np.uint8)
    img_ycbcr = np.asarray(pil.convert("YCbCr"), dtype=np.uint8)

    pyramid = [img_gray]
    cur = pil.convert("L")
    while min(cur.size) > 32:
        cur = cur.resize((max(1, cur.size[0] // 2), max(1, cur.size[1] // 2)), Image.BILINEAR)
        pyramid.append(np.asarray(cur, dtype=np.uint8))

    jpeg90 = None
    try:
        buf = io.BytesIO()
        pil.save(buf, "JPEG", quality=90)
        jpeg90 = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"), dtype=np.uint8)
    except Exception:
        jpeg90 = None

    return PreprocCache(
        img_orig=img_rgb,
        img_gray=img_gray,
        img_ycbcr=img_ycbcr,
        pyramid=pyramid,
        jpeg_reenc_90=jpeg90,
    )

