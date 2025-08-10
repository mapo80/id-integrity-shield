"""Copy-move detection with optional preprocessing cache."""

from __future__ import annotations

import numpy as np

from ..preproc import PreprocCache


def _dh(b, ham_tol=4):
    """Compute 64-bit dHash for a tiny grayscale block (9x8)."""
    H, W = b.shape
    h, w = 8, 9
    ys = np.linspace(0, H, h + 1, dtype=int)
    xs = np.linspace(0, W, w + 1, dtype=int)
    small = np.zeros((h, w), dtype=np.float32)
    for i in range(h):
        for j in range(w):
            patch = b[ys[i] : ys[i + 1], xs[j] : xs[j + 1]]
            small[i, j] = float(patch.mean()) if patch.size else 0.0
    bits = (small[:, 1:] > small[:, :-1]).astype(np.uint8)
    num = 0
    for i in range(8):
        for j in range(8):
            num = (num << 1) | int(bits[i, j])
    return np.uint64(num)


def _hamming(a, b):
    v = np.uint64(a ^ b)
    cnt = 0
    while v:
        v &= v - np.uint64(1)
        cnt += 1
    return cnt


def run(img_or_cache, params=None):
    """Run the copy-move check."""

    p = params or {}
    mode = p.get("mode", "block")
    top_percent = float(p.get("top_percent", 2.0))

    if isinstance(img_or_cache, PreprocCache):
        arr = img_or_cache.gray.astype(np.float32) / 255.0
    else:
        arr = np.asarray(img_or_cache.convert("L"), dtype=np.float32) / 255.0

    H, W = arr.shape

    if mode == "orb":
        try:
            import cv2
        except Exception as e:
            return _run_block(arr, p, top_percent, fallback_reason=f"opencv not available: {e}")
        return _run_orb(arr, p, top_percent)

    return _run_block(arr, p, top_percent)


def _run_block(arr, p, top_percent, fallback_reason=None):
    H, W = arr.shape
    B = int(p.get("block", 16))
    S = int(p.get("step", 8))
    ham_tol = int(p.get("ham_tol", 6))
    min_off = int(p.get("min_offset", 12))
    max_pairs = int(p.get("max_pairs", 4000))
    min_cluster = int(p.get("min_cluster", 12))
    dilate = int(p.get("dilate", 2))

    ys = list(range(0, max(1, H - B + 1), S))
    xs = list(range(0, max(1, W - B + 1), S))
    locs = []
    hashes = []
    means = []
    std_min = float(p.get("std_min", 0.02))
    for y in ys:
        for x in xs:
            patch = arr[y : y + B, x : x + B]
            if patch.std() < std_min:
                continue
            h = _dh(patch)
            locs.append((y, x))
            hashes.append(h)
            means.append(float(patch.mean()))
    locs = np.array(locs, dtype=np.int32)
    hashes = np.array(hashes, dtype=np.uint64)
    means = np.array(means, dtype=np.float32)

    bucket_keys = (hashes >> np.uint64(40)).astype(np.uint32)
    buckets = {}
    for idx, key in enumerate(bucket_keys):
        buckets.setdefault(int(key), []).append(idx)

    matches = []
    for key, idxs in buckets.items():
        n = len(idxs)
        if n < 2:
            continue
        pairs_est = n * (n - 1) // 2
        if pairs_est > 2 * max_pairs:
            import math

            k = int((1 + math.isqrt(1 + 8 * max_pairs)) // 2)
            idxs = idxs[: max(2, k)]
            n = len(idxs)
        cnt_pairs = 0
        for ii in range(n - 1):
            i = idxs[ii]
            hi = hashes[i]
            mi = means[i]
            yi, xi = locs[i]
            for jj in range(ii + 1, n):
                j = idxs[jj]
                yj, xj = locs[j]
                dy = yj - yi
                dx = xj - xi
                if abs(dy) + abs(dx) < min_off:
                    continue
                hd = _hamming(int(hi), int(hashes[j]))
                if hd <= ham_tol and abs(mi - means[j]) < 0.08:
                    matches.append((yi, xi, yj, xj, dy, dx))
                    cnt_pairs += 1
                    if cnt_pairs >= max_pairs:
                        break
            if cnt_pairs >= max_pairs:
                break

    from collections import defaultdict

    clusters = defaultdict(list)
    for yi, xi, yj, xj, dy, dx in matches:
        clusters[(int(dy), int(dx))].append((yi, xi, yj, xj))

    strong = [(vec, pts) for vec, pts in clusters.items() if len(pts) >= min_cluster]
    hm = np.zeros((H, W), dtype=np.float32)
    for (dy, dx), pts in strong:
        for (yi, xi, yj, xj) in pts:
            hm[yi : yi + B, xi : xi + B] += 1.0
            hm[yj : yj + B, xj : xj + B] += 1.0

    if hm.max() > 0:
        for _ in range(max(0, int(dilate))):
            pad = np.pad(hm, 1, mode="edge")
            hm = np.maximum.reduce(
                [
                    pad[0:-2, 0:-2],
                    pad[0:-2, 1:-1],
                    pad[0:-2, 2:],
                    pad[1:-1, 0:-2],
                    pad[1:-1, 1:-1],
                    pad[1:-1, 2:],
                    pad[2:, 0:-2],
                    pad[2:, 1:-1],
                    pad[2:, 2:],
                ]
            )
        hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)

    flat = hm.flatten()
    k = max(1, int(len(flat) * top_percent / 100.0))
    topk = np.partition(flat, -k)[-k:]
    score = float(np.clip(topk.mean(), 0.0, 1.0))

    meta = {
        "mode": "block",
        "blocks": int(len(locs)),
        "matches": int(len(matches)),
        "clusters": int(len(strong)),
        "top_percent": top_percent,
    }
    if fallback_reason:
        meta["fallback_reason"] = str(fallback_reason)

    return {"name": "copy_move", "score": score, "map": hm, "meta": meta}


def _run_orb(arr, p, top_percent):
    import cv2

    H, W = arr.shape
    min_cluster = int(p.get("min_cluster", 8))
    orb = cv2.ORB_create(nfeatures=2000, scaleFactor=1.2, nlevels=8)
    kps, des = orb.detectAndCompute((arr * 255).astype("uint8"), None)
    if des is None or len(kps) < 8:
        return {
            "name": "copy_move",
            "score": 0.0,
            "map": np.zeros_like(arr),
            "meta": {"mode": "orb", "reason": "no keypoints"},
        }
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des, des)
    good = [m for m in matches if m.queryIdx != m.trainIdx]
    from collections import defaultdict

    clusters = defaultdict(list)
    for m in good:
        pt1 = kps[m.queryIdx].pt
        pt2 = kps[m.trainIdx].pt
        dx = int(round(pt2[0] - pt1[0]))
        dy = int(round(pt2[1] - pt1[1]))
        if abs(dx) + abs(dy) < 6:
            continue
        clusters[(dy, dx)].append((pt1, pt2))

    strong = [(vec, pts) for vec, pts in clusters.items() if len(pts) >= min_cluster]
    hm = np.zeros((H, W), dtype=np.float32)
    for (dy, dx), pts in strong:
        for (p1, p2) in pts:
            y1, x1 = int(round(p1[1])), int(round(p1[0]))
            y2, x2 = int(round(p2[1])), int(round(p2[0]))
            if 0 <= y1 < H and 0 <= x1 < W:
                hm[max(0, y1 - 4) : min(H, y1 + 4), max(0, x1 - 4) : min(W, x1 + 4)] += 1.0
            if 0 <= y2 < H and 0 <= x2 < W:
                hm[max(0, y2 - 4) : min(H, y2 + 4), max(0, x2 - 4) : min(W, x2 + 4)] += 1.0
    if hm.max() > 0:
        hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)
    flat = hm.flatten()
    k = max(1, int(len(flat) * top_percent / 100.0))
    topk = np.partition(flat, -k)[-k:]
    score = float(np.clip(topk.mean(), 0.0, 1.0))
    return {
        "name": "copy_move",
        "score": score,
        "map": hm,
        "meta": {"mode": "orb", "clusters": len(strong), "kp": len(kps)},
    }

