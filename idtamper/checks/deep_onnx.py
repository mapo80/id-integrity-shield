import numpy as np

from ..execution import ParallelConfig, init_onnx_session_opts


def run(pil_image, params=None):
    p = params or {}
    model_path = p.get("model_path", None)
    if not model_path:
        return {
            "name": "deep_onnx",
            "score": None,
            "map": None,
            "meta": {"reason": "model_path not provided"},
        }
    try:
        import onnxruntime as ort

        so = init_onnx_session_opts(ParallelConfig())
        sess = ort.InferenceSession(
            str(model_path), sess_options=so, providers=["CPUExecutionProvider"]
        )
    except Exception as e:
        return {
            "name": "deep_onnx",
            "score": None,
            "map": None,
            "meta": {"reason": f"onnxruntime/model error: {e}"},
        }
    in_name = sess.get_inputs()[0].name
    out_name = sess.get_outputs()[0].name
    from PIL import Image

    H, W = p.get("input_size", [256, 256])
    arr = np.asarray(pil_image.convert("RGB"))
    arr = (
        np.array(Image.fromarray(arr).resize((W, H), Image.BILINEAR), dtype=np.float32)
        / 255.0
    )
    x = np.transpose(arr, (2, 0, 1))[None, ...].astype(np.float32)
    y = sess.run([out_name], {in_name: x})[0]
    y = np.squeeze(y)
    try:
        if y.ndim == 0:
            score = float(y)
        elif y.ndim == 1:
            score = float(y.max())
        else:
            score = float(y.mean())
    except Exception:
        score = float(np.mean(y))
    score = max(0.0, min(1.0, score))
    return {"name": "deep_onnx", "score": score, "map": None, "meta": {"input_size": [H, W]}}