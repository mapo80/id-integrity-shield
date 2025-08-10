import numpy as np
from PIL import Image

from ..execution import ParallelConfig, init_onnx_session_opts

def _mock_forward(H, W, seed=0):
    rng = np.random.RandomState(seed)
    base = rng.randn(H, W).astype(np.float32) * 0.1
    yy, xx = np.mgrid[0:H, 0:W]
    base += 0.3 * np.sin(2 * np.pi * yy / 32.0) * np.cos(2 * np.pi * xx / 32.0)
    return base.astype(np.float32)

def run(pil_image, params=None):
    p = params or {}
    mock = bool(p.get('mock', False))
    top_percent = float(p.get('score_top_percent', 5.0))
    blk = int(p.get('block', 32))
    if mock:
        Ht, Wt = p.get('input_size', [512, 512])
        resid = _mock_forward(Ht, Wt, seed=321)
    else:
        sess = p.get("session")
        mp = p.get("model_path", None)
        if sess is None:
            if not mp:
                return {
                    "name": "noiseprintpp",
                    "score": None,
                    "map": None,
                    "meta": {"reason": "model_path not provided"},
                }
            try:
                import onnxruntime as ort

                so = init_onnx_session_opts(ParallelConfig())
                sess = ort.InferenceSession(
                    str(mp), sess_options=so, providers=["CPUExecutionProvider"]
                )
            except Exception as e:
                return {
                    "name": "noiseprintpp",
                    "score": None,
                    "map": None,
                    "meta": {"reason": f"onnxruntime/model error: {e}"},
                }
        in_name = sess.get_inputs()[0].name
        out_name = sess.get_outputs()[0].name
        arr = np.asarray(pil_image.convert('RGB'))
        Ht, Wt = (p.get('input_size') or [arr.shape[0], arr.shape[1]])
        arr = np.array(Image.fromarray(arr).resize((Wt, Ht), Image.BILINEAR), dtype=np.float32) / 255.0
        x = np.transpose(arr, (2, 0, 1))[None, ...].astype(np.float32)
        resid = sess.run([out_name], {in_name: x})[0]
        resid = np.squeeze(resid).astype(np.float32)
        if resid.ndim == 3:
            resid = resid[0] if resid.shape[0] <= 3 else resid.mean(axis=0)
    H, W = resid.shape[:2]
    emap = np.zeros((H, W), dtype=np.float32)
    for y in range(0, H, blk):
        for x in range(0, W, blk):
            patch = resid[y:y + blk, x:x + blk]
            emap[y:y + blk, x:x + blk] = float(np.std(patch))
    emap = (emap - emap.min()) / (emap.max() - emap.min() + 1e-8)
    flat = emap.flatten()
    k = max(1, int(len(flat) * top_percent / 100.0))
    topk = np.partition(flat, -k)[-k:]
    score = float(np.clip(topk.mean(), 0.0, 1.0))
    W0, H0 = pil_image.size
    emap_rs = np.array(Image.fromarray((emap * 255).astype('uint8')).resize((W0, H0), Image.BILINEAR), dtype=np.float32) / 255.0
    return {"name": "noiseprintpp", "score": score, "map": emap_rs, "meta": {"block": blk, "top_percent": top_percent}}
