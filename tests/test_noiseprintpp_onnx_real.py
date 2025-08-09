def main():
    import os
    from pathlib import Path
    try:
        import onnxruntime as ort  # noqa: F401
    except Exception as e:
        print("SKIP: onnxruntime not installed:", e)
        return True

    mp = os.environ.get("NOISEPRINTPP_ONNX_PATH", "/mnt/data/models/noiseprintpp.onnx")
    mp = Path(mp)
    if not mp.exists():
        print("SKIP: Noiseprint++ ONNX file not found at", mp)
        return True

    from idtamper.pipeline import analyze_image, AnalyzerConfig
    from idtamper.profiles import load_profile
    from PIL import Image
    import numpy as np

    tmp = Path("/mnt/data/idtamper/tmp_noisepp_real"); tmp.mkdir(parents=True, exist_ok=True)
    img = tmp/"rand.png"
    arr = (np.random.rand(480, 720, 3)*255).astype("uint8"); Image.fromarray(arr).save(img)

    prof = load_profile("recapture-id")
    params = prof["params"]
    params["noiseprintpp"] = {**params["noiseprintpp"], "model_path": str(mp), "input_size": None, "score_top_percent": 5.0, "block": 32}
    params["trufor"]["model_path"] = None
    # deep_onnx removed

    cfg = AnalyzerConfig(weights=prof["weights"], threshold=prof["threshold"], check_params=params, check_thresholds=prof["thresholds"])
    rep = analyze_image(str(img), str(tmp/"out"), cfg)

    npp = rep["per_check"]["noiseprintpp"]
    assert npp["score"] is not None and 0.0 <= npp["score"] <= 1.0
    assert rep["artifacts"].get("heatmap_noiseprintpp") is not None
    print("OK Noiseprint++ ONNX score:", npp["score"])
    return True

if __name__ == "__main__":
    print(main())