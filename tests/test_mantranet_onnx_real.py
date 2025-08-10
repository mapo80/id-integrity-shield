def main():
    import os
    from pathlib import Path
    try:
        import onnxruntime as ort  # noqa: F401
    except Exception as e:
        print("SKIP: onnxruntime not installed:", e)
        return True
    mp = os.environ.get("MANTRANET_ONNX_PATH")
    if not mp or not Path(mp).exists():
        print("SKIP: MANTRANET_ONNX_PATH not set or missing file")
        return True

    from idtamper.pipeline import AnalyzerConfig, analyze_image
    from idtamper.profiles import load_profile
    from PIL import Image
    import numpy as np

    tmp = Path('/mnt/data/idtamper/tmp_mtr'); tmp.mkdir(parents=True, exist_ok=True)
    img = tmp/'img.png'; Image.fromarray((np.random.rand(512,512,3)*255).astype('uint8')).save(img)
    prof = load_profile('recapture-id')
    params = prof['params']
    params['mantranet'] = {**params['mantranet'], 'model_path': mp, 'input_size':[256,256]}
    # disable heavy checks for speed
    params['noiseprintpp']['model_path'] = None

    cfg = AnalyzerConfig(weights=prof['weights'], threshold=prof['threshold'], check_params=params, check_thresholds=prof['thresholds'])
    rep = analyze_image(str(img), str(tmp/'out'), cfg)
    mt = rep['per_check']['mantranet']
    assert mt['score'] is not None and 0.0 <= mt['score'] <= 1.0
    assert rep['artifacts'].get('heatmap_mantranet') is not None
    return True

if __name__=='__main__':
    print(main())