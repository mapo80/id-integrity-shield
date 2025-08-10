
import numpy as np

def run(pil_image, params=None):
    """ManTraNet ONNX check (CPU). 
    - If 'model_path' provided and onnxruntime available -> run model.
    - Else if 'mock'==True -> synthetic heatmap for tests.
    - Else -> return score=None with reason.
    Params:
      model_path: str | None
      input_size: [H,W] (default [512,512])
      top_percent: float (default 1.0)
      mock: bool (default False)
    Output: {name:'mantranet', score, map, meta}
    """
    p = params or {}
    top_percent = float(p.get('top_percent', 1.0))
    Ht, Wt = (p.get('input_size') or [512,512])
    model_path = p.get('model_path')
    mock = bool(p.get('mock', False))

    if model_path:
        try:
            import onnxruntime as ort
            from PIL import Image
            sess = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
            im = pil_image.convert('RGB').resize((Wt, Ht))
            arr = (np.asarray(im).astype('float32')/255.0)
            inp = sess.get_inputs()[0]
            shape = inp.shape
            channels_first = len(shape) >= 4 and shape[1] == 3
            if channels_first:
                x = np.transpose(arr, (2,0,1))[None, ...]  # NCHW
            else:
                # default to channels-last (NHWC)
                x = arr[None, ...]
            feeds = {inp.name: x}
            outs = sess.run(None, feeds)
            y = outs[0]
            # Accept common cases: (N,1,h,w) | (N,h,w,1) | (N,h,w) | (1,h,w) | (h,w)
            y = np.asarray(y)
            y = np.squeeze(y)
            if y.ndim == 3:  # (C,H,W) assume C=1
                y = y[0] if y.shape[0] in (1,2,3) else y[0]
            if y.ndim != 2:
                # Fallback: attempt last 2 dims as map
                y = y.reshape((y.shape[-2], y.shape[-1]))
            hm = y.astype('float32')
            # normalize to [0,1]
            hm = hm - hm.min()
            denom = (hm.max()-hm.min()+1e-8)
            hm = hm/denom
            # score by top-percentile
            flat = hm.flatten()
            k = max(1, int(len(flat)*top_percent/100.0))
            topk = np.partition(flat, -k)[-k:]
            score = float(np.clip(topk.mean(), 0.0, 1.0))
            return {"name":"mantranet","score":score,"map":hm,"meta":{"input_size":[Ht,Wt],"top_percent":top_percent}}
        except Exception as e:
            return {"name":"mantranet","score":None,"map":None,"meta":{"reason":str(e)}}
    if mock:
        # simple center blob heatmap to exercise the pipeline
        H,W = pil_image.size[1], pil_image.size[0]
        yy, xx = np.mgrid[0:H, 0:W]
        cy, cx = H/2.0, W/2.0
        r2 = (yy-cy)**2 + (xx-cx)**2
        hm = np.exp(-r2/(2*(0.15*max(H,W))**2)).astype('float32')
        flat = hm.flatten()
        k = max(1, int(len(flat)*top_percent/100.0))
        score = float(np.partition(flat, -k)[-k:].mean())
        return {"name":"mantranet","score":score,"map":hm,"meta":{"mock":True,"top_percent":top_percent}}
    return {"name":"mantranet","score":None,"map":None,"meta":{"reason":"no model and no mock"}}
