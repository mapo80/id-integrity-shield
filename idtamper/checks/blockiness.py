import numpy as np

def run(pil_image, params=None):
    p = params or {}
    q = int(p.get("q", 8))
    arr = np.asarray(pil_image.convert("L"), dtype=np.float32)
    H,W = arr.shape
    gy = np.abs(np.diff(arr, axis=0, prepend=arr[:1,:]))
    gx = np.abs(np.diff(arr, axis=1, prepend=arr[:, :1]))
    bm = np.zeros_like(arr, dtype=np.float32)
    for y in range(0, H, q):
        bm[y:y+1,:] += gy[y:y+1,:]
    for x in range(0, W, q):
        bm[:,x:x+1] += gx[:,x:x+1]
    hm = (bm - bm.min())/(bm.max()-bm.min()+1e-8)
    on = bm[(np.indices(bm.shape)[0]%q==0) | (np.indices(bm.shape)[1]%q==0)]
    off = bm[(np.indices(bm.shape)[0]%q!=0) & (np.indices(bm.shape)[1]%q!=0)]
    on_m = float(on.mean()) if on.size else 0.0
    off_m = float(off.mean()) if off.size else 0.0
    std = float(bm.std()+1e-6)
    score = max(0.0, min(1.0, (on_m - off_m)/std))
    return {"name":"jpeg_blockiness","score": score, "map": hm, "meta": {"q": q, "on_mean": on_m, "off_mean": off_m, "std": std}}