
import numpy as np
import logging

logger = logging.getLogger(__name__)

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
    session = p.get('session')
    model_path = p.get('model_path')
    mock = bool(p.get('mock', False))

    if session is None and model_path:
        try:
            import onnxruntime as ort
            session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
            logger.info("ManTraNet model loaded from %s", model_path)
        except Exception as e:
            logger.error("ManTraNet failed to load model %s: %s", model_path, e)
            return {"name":"mantranet","score":None,"map":None,"meta":{"reason":str(e)}}

    if session is not None:
        try:
            im = pil_image.convert('RGB').resize((Wt, Ht))
            arr = (np.asarray(im).astype('float32')/255.0)
            inp = session.get_inputs()[0]
            shape = inp.shape
            channels_first = len(shape) >= 4 and shape[1] == 3
            if channels_first:
                x = np.transpose(arr, (2,0,1))[None, ...]  # NCHW
            else:
                x = arr[None, ...]
            feeds = {inp.name: x}
            outs = session.run(None, feeds)
            y = outs[0]
            y = np.asarray(y)
            y = np.squeeze(y)
            if y.ndim == 3:
                y = y[0] if y.shape[0] in (1,2,3) else y[0]
            if y.ndim != 2:
                y = y.reshape((y.shape[-2], y.shape[-1]))
            hm = y.astype('float32')
            hm = hm - hm.min()
            denom = (hm.max()-hm.min()+1e-8)
            hm = hm/denom
            flat = hm.flatten()
            k = max(1, int(len(flat)*top_percent/100.0))
            topk = np.partition(flat, -k)[-k:]
            score = float(np.clip(topk.mean(), 0.0, 1.0))
            logger.info("ManTraNet inference completed: score=%.4f", score)
            return {"name":"mantranet","score":score,"map":hm,"meta":{"input_size":[Ht,Wt],"top_percent":top_percent}}
        except Exception as e:
            logger.error("ManTraNet inference failed: %s", e)
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
        logger.info("ManTraNet mock mode: score=%.4f", score)
        return {"name":"mantranet","score":score,"map":hm,"meta":{"mock":True,"top_percent":top_percent}}
    logger.warning("ManTraNet skipped: no model available and mock disabled")
    return {"name":"mantranet","score":None,"map":None,"meta":{"reason":"no model and no mock"}}
