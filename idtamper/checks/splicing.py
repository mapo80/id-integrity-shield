"""Splicing detection with optional preprocessing cache."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

def _gradients(arr):
    gy = np.abs(np.diff(arr, axis=0, prepend=arr[:1, :]))
    gx = np.abs(np.diff(arr, axis=1, prepend=arr[:, :1]))
    return gx, gy


def _structure_coherence(gx, gy, win=5, eps=1e-6):
    H, W = gx.shape
    Ixx = gx * gx
    Iyy = gy * gy
    Ixy = gx * gy

    def boxblur(M, w):
        w = int(w) | 1
        pad = w // 2
        P = np.pad(M, ((pad, pad), (pad, pad)), mode="edge")
        I = np.cumsum(np.cumsum(P, axis=0), axis=1)
        I = np.pad(I, ((1, 0), (1, 0)), mode="constant", constant_values=0)
        S = I[w:, w:] - I[:-w, w:] - I[w:, :-w] + I[:-w, :-w]
        return S / float(w * w)

    Ixx_b = boxblur(Ixx, win)
    Iyy_b = boxblur(Iyy, win)
    Ixy_b = boxblur(Ixy, win)
    tr = Ixx_b + Iyy_b
    det = Ixx_b * Iyy_b - Ixy_b * Ixy_b
    tmp = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    l1 = tr / 2.0 + tmp
    l2 = tr / 2.0 - tmp
    coh = (l1 - l2) / (l1 + l2 + eps)
    return np.clip(coh, 0.0, 1.0)


def run(img_or_cache, params=None):
    p = params or {}
    mode = p.get("mode", "multiscale")
    max_side = int(p.get("max_side", 1024))
    top_percent = float(p.get("top_percent", 1.0))
    scales = p.get("scales", [1.0, 2.0, 4.0])
    win = int(p.get("win", 7))

    if hasattr(img_or_cache, "img") and hasattr(img_or_cache, "ycbcr"):
        im = Image.fromarray(img_or_cache.img)
        arr = img_or_cache.ycbcr.astype(np.float32)
    else:
        im = img_or_cache
        arr = np.asarray(im.convert("YCbCr"), dtype=np.float32)

    W0, H0 = im.size
    scale = 1.0
    if max(W0, H0) > max_side:
        scale = max_side / float(max(W0, H0))
        im = im.resize((int(W0 * scale), int(H0 * scale)), Image.BILINEAR)
        arr = np.asarray(im.convert("YCbCr"), dtype=np.float32)
    Y, U, V = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    if mode == "classic":
        def grad(a):
            return np.hypot(
                np.diff(a, axis=0, prepend=a[:1, :]),
                np.diff(a, axis=1, prepend=a[:, :1]),
            )

        gY, gU, gV = grad(Y), grad(U), grad(V)
        varY = Y - Y.mean()
        varU = U - U.mean()
        varV = V - V.mean()
        m = gY * np.abs(varY) + 0.5 * gU * np.abs(varU) + 0.5 * gV * np.abs(varV)
        hm = (m - m.min()) / (m.max() - m.min() + 1e-8)
    else:
        acc = np.zeros_like(Y, dtype=np.float32)
        for s in scales:
            if s > 0:
                Ys = np.asarray(
                    im.filter(ImageFilter.GaussianBlur(radius=float(s))).convert("L"),
                    dtype=np.float32,
                )
                Us = U
                Vs = V
            else:
                Ys = Y
                Us = U
                Vs = V
            gxY, gyY = _gradients(Ys)
            gY = np.hypot(gxY, gyY)
            coh = _structure_coherence(gxY, gyY, win=max(3, win))
            acc += (gY * (1.0 - coh)).astype(np.float32)
            gxU, gyU = _gradients(Us)
            gxV, gyV = _gradients(Vs)
            acc += 0.25 * (np.hypot(gxU, gyU) + np.hypot(gxV, gyV)).astype(np.float32)
        hm = (acc - acc.min()) / (acc.max() - acc.min() + 1e-8)

    flat = hm.flatten()
    k = max(1, int(len(flat) * top_percent / 100.0))
    topk = np.partition(flat, -k)[-k:]
    score = float(np.clip(topk.mean(), 0.0, 1.0))

    hm = (
        np.array(Image.fromarray((hm * 255).astype("uint8")).resize((W0, H0), Image.BILINEAR), dtype=np.float32)
        / 255.0
    )
    return {
        "name": "splicing",
        "score": score,
        "map": hm,
        "meta": {"mode": mode, "scales": scales, "win": win, "top_percent": top_percent},
    }

