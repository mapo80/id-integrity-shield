
import numpy as np
from PIL import ImageFilter

def _haar2d(x):
    # Simple 1-level Haar DWT producing LL, (LH, HL, HH)
    # Assumes 2D float array with even sizes; pad if needed
    H,W = x.shape
    if H%2==1: x = np.pad(x, ((0,1),(0,0)), mode='edge'); H+=1
    if W%2==1: x = np.pad(x, ((0,0),(0,1)), mode='edge'); W+=1
    # 1D along rows
    a = (x[:,0::2] + x[:,1::2]) * 0.5
    d = (x[:,0::2] - x[:,1::2]) * 0.5
    # then along columns
    LL = (a[0::2,:] + a[1::2,:]) * 0.5
    LH = (d[0::2,:] + d[1::2,:]) * 0.5
    HL = (a[0::2,:] - a[1::2,:]) * 0.5
    HH = (d[0::2,:] - d[1::2,:]) * 0.5
    return LL, LH, HL, HH

def _local_stats(M, block=16, step=8):
    H,W = M.shape
    S = np.zeros_like(M, dtype=np.float32)
    for y in range(0, H, step):
        for x in range(0, W, step):
            patch = M[y:y+block, x:x+block]
            S[y:y+step, x:x+step] = float(np.std(patch))
    return S

def run(pil_image, params=None):
    """
    Enhanced Noise Inconsistency.
    Methods:
      - 'wavelet' (default): std map sulla somma dei subband ad alta frequenza (LH+HL+HH)
      - 'blur': residuo (img - GaussianBlur)
    Params:
      - method: 'wavelet' | 'blur'
      - block: 32, step: 16 (per la mappa std)
      - blur_radius: 1.0 (se method='blur')
      - top_percent: 5.0
    """
    p = params or {}
    method = p.get('method', 'wavelet')
    block = int(p.get('block', 32))
    step = int(p.get('step', 16))
    top_percent = float(p.get('top_percent', 5.0))

    arr = np.asarray(pil_image.convert("L"), dtype=np.float32)/255.0

    if method == 'blur':
        blur = float(p.get('blur_radius', 1.0))
        from PIL import ImageFilter
        arr_blur = np.asarray(pil_image.convert("L").filter(ImageFilter.GaussianBlur(radius=blur)), dtype=np.float32)/255.0
        resid = np.abs(arr - arr_blur)
        energy = resid
    else:
        # wavelet residual energy
        LL, LH, HL, HH = _haar2d(arr)
        energy = np.abs(LH) + np.abs(HL) + np.abs(HH)

    stdmap = _local_stats(energy, block=block, step=step)
    hm = (stdmap - stdmap.min())/(stdmap.max()-stdmap.min()+1e-8)

    flat = hm.flatten()
    k = max(1, int(len(flat)*top_percent/100.0))
    topk = np.partition(flat, -k)[-k:]
    score = float(np.clip(topk.mean(), 0.0, 1.0))

    return {"name":"noise_inconsistency", "score": score, "map": hm, "meta": {"method": method, "block": block, "step": step, "top_percent": top_percent}}
