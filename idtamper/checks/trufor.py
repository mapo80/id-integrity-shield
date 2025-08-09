import numpy as np
from PIL import Image

def _mock_forward(H, W, seed=0):
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    cy, cx = H//2, W//2
    d2 = ((yy-cy)**2 + (xx-cx)**2) / float((0.2*H)*(0.2*W) + 1e-6)
    heat = np.exp(-d2).astype(np.float32) * 0.6 + rng.rand(H,W).astype(np.float32)*0.1
    rel = np.clip(1.0 - (d2/np.max(d2+1e-6)), 0, 1).astype(np.float32)
    return heat, rel

def run(pil_image, params=None):
    p = params or {}
    mock = bool(p.get('mock', False))
    Ht,Wt = p.get('input_size', [480,480])
    top_percent = float(p.get('score_top_percent', 1.0))
    w_rel = float(p.get('reliability_weight', 0.5))

    if mock:
        hm, rel = _mock_forward(Ht, Wt, seed=123)
    else:
        mp = p.get('model_path', None)
        if not mp:
            return {"name":"trufor","score": None,"map": None,"meta": {"reason":"model_path not provided"}}
        try:
            import onnxruntime as ort
            sess = ort.InferenceSession(str(mp), providers=['CPUExecutionProvider'])
        except Exception as e:
            return {"name":"trufor","score": None,"map": None,"meta": {"reason": f"onnxruntime/model error: {e}"}}
        in_name = sess.get_inputs()[0].name
        out_name = p.get('output_key', sess.get_outputs()[0].name)
        arr = np.asarray(pil_image.convert('RGB'))
        arr = np.array(Image.fromarray(arr).resize((Wt,Ht), Image.BILINEAR), dtype=np.float32)/255.0
        x = np.transpose(arr, (2,0,1))[None,...].astype(np.float32)
        y = sess.run([out_name], {in_name: x})[0]
        y = np.squeeze(y)
        if y.ndim==2:
            hm = y.astype(np.float32); rel = np.ones_like(hm, dtype=np.float32)
        elif y.ndim==3:
            if y.shape[0] in (1,2):
                C,H,W = y.shape; hm = y[0]; rel = y[1] if C>1 else np.ones((H,W), dtype=np.float32)
            elif y.shape[2] in (1,2):
                H,W,C = y.shape; hm = y[:,:,0]; rel = y[:,:,1] if C>1 else np.ones((H,W), dtype=np.float32)
            else:
                hm = y.mean(axis=0); rel = np.ones_like(hm, dtype=np.float32)
        else:
            N = int(np.sqrt(y.size)); hm = y.reshape(N, -1).astype(np.float32); rel = np.ones_like(hm, dtype=np.float32)

    hm = np.clip(hm, 0, 1).astype(np.float32); rel = np.clip(rel, 0, 1).astype(np.float32)
    fused = (1.0 - w_rel)*hm + w_rel*(hm*rel)

    flat = fused.flatten()
    k = max(1, int(len(flat)*top_percent/100.0))
    topk = np.partition(flat, -k)[-k:]
    score = float(np.clip(topk.mean(), 0.0, 1.0))

    # resize to original
    W0,H0 = pil_image.size
    fused_rs = np.array(Image.fromarray((fused*255).astype('uint8')).resize((W0,H0), Image.BILINEAR), dtype=np.float32)/255.0
    return {"name":"trufor","score": score,"map": fused_rs,"meta": {"input_size":[Ht,Wt], "top_percent": top_percent, "rel_weight": w_rel}}