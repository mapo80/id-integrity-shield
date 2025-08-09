def main():
    import os
    from pathlib import Path
    try:
        import onnxruntime as ort  # noqa: F401
    except Exception as e:
        print("SKIP: onnxruntime not installed:", e)
        return True

    # model path from env or common default
    mp = os.environ.get("TRUFOR_ONNX_PATH", "/mnt/data/models/trufor_480x480_op13.onnx")
    mp = Path(mp)
    if not mp.exists():
        print("SKIP: TruFor ONNX file not found at", mp)
        return True

    from idtamper.pipeline import analyze_image, AnalyzerConfig
    from idtamper.profiles import load_profile
    from PIL import Image, ImageDraw

    tmp = Path("/mnt/data/idtamper/tmp_trufor_real"); tmp.mkdir(parents=True, exist_ok=True)
    img = tmp/"doc.png"
    im = Image.new("RGB", (640, 400), "white")
    dr = ImageDraw.Draw(im); dr.rectangle([180,120,460,280], outline="black", width=6); dr.text((200,150), "ID CARD", fill="black")
    im.save(img)

    prof = load_profile("recapture-id")
    params = prof["params"]
    params["trufor"] = {**params["trufor"], "model_path": str(mp), "input_size":[480,480], "score_top_percent": 1.0}
    # keep noiseprintpp/deep_onnx disabled for speed
    params["noiseprintpp"]["model_path"] = None
    # deep_onnx removed

    cfg = AnalyzerConfig(weights=prof["weights"], threshold=prof["threshold"], check_params=params, check_thresholds=prof["thresholds"])
    rep = analyze_image(str(img), str(tmp/"out"), cfg)

    tf = rep["per_check"]["trufor"]
    assert tf["score"] is not None and 0.0 <= tf["score"] <= 1.0
    assert rep["artifacts"].get("heatmap_trufor") is not None
    assert rep["artifacts"].get("overlay") is not None
    print("OK TruFor ONNX score:", tf["score"])
    return True

if __name__ == "__main__":
    print(main())