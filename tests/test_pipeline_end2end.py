def main():
    from pathlib import Path
    from idtamper.pipeline import analyze_image, AnalyzerConfig
    from idtamper.profiles import load_profile
    from PIL import Image, ImageDraw

    repo_root = Path(__file__).resolve().parents[1]
    tmp = repo_root/'tmp_e2e'; tmp.mkdir(parents=True, exist_ok=True)
    # Two images: one 'tampered' path, one 'genuine' path (labels inferred by scan_dataset, not here)
    img1 = tmp/'tampered'/ 'doc1.png'; img1.parent.mkdir(parents=True, exist_ok=True)
    img2 = tmp/'genuine'/ 'doc2.png'; img2.parent.mkdir(parents=True, exist_ok=True)

    def mk(im_path, with_text=True):
        im = Image.new('RGB', (512, 320), 'white')
        dr = ImageDraw.Draw(im)
        dr.rectangle([120,80,392,240], outline='black', width=5)
        if with_text: dr.text((140,120), "ID 123456", fill='black')
        im.save(im_path)
    mk(img1, True); mk(img2, False)

    prof = load_profile('recapture-id')
    params = prof['params']
    # enable mocks for ONNX checks to hit their paths
    params['trufor'] = {**params['trufor'], 'mock': True, 'input_size':[384,384]}
    params['noiseprintpp'] = {**params['noiseprintpp'], 'mock': True, 'input_size':[512,512]}

    cfg = AnalyzerConfig(weights=prof['weights'], threshold=prof['threshold'],
                         check_params=params, check_thresholds=prof['thresholds'])

    r1 = analyze_image(str(img1), str(tmp/'out1'), cfg)
    r2 = analyze_image(str(img2), str(tmp/'out2'), cfg)

    assert 'per_check' in r1 and 'artifacts' in r1 and 'overlay' in r1['artifacts']
    assert 'fused_heatmap' in r2['artifacts']
    # flags must be consistent with thresholds type
    for rep in (r1, r2):
        for k,v in rep['per_check'].items():
            sc = v['score']; th = v['threshold']
            if sc is not None:
                assert isinstance(th, float)
                assert isinstance(v['flag'], bool)
    return True

if __name__ == "__main__":
    print(main())