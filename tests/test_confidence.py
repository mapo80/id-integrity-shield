def main():
    from pathlib import Path
    from idtamper.pipeline import analyze_image, AnalyzerConfig
    from idtamper.profiles import load_profile
    from PIL import Image, ImageDraw

    tmp = Path('/mnt/data/idtamper/tmp_conf'); tmp.mkdir(parents=True, exist_ok=True)
    img = tmp/'doc.png'
    im = Image.new('RGB', (640, 400), 'white')
    dr = ImageDraw.Draw(im); dr.rectangle([180,120,460,280], outline='black', width=6); dr.text((200,150), 'ID CARD', fill='black')
    im.save(img)

    prof = load_profile('recapture-id')
    params = prof['params']
    params['noiseprintpp'] = {**params['noiseprintpp'], 'mock': True, 'input_size':[512,512]}
    # Encourage flagging by lowering thresholds a bit
    thr = prof['thresholds']
    thr['noiseprintpp'] = 0.3
    thr['copy_move'] = -0.1

    cfg = AnalyzerConfig(weights=prof['weights'], threshold=prof['threshold'], check_params=params, check_thresholds=thr)
    out = tmp/'out'; out.mkdir(parents=True, exist_ok=True)
    rep = analyze_image(str(img), str(out), cfg)

    assert 'confidence' in rep and 0.0 <= rep['confidence'] <= 1.0
    # with two strong checks likely flagged, confidence should be reasonably high
    if rep['per_check']['copy_move']['flag'] and rep['per_check']['noiseprintpp']['flag']:
        assert rep['confidence'] >= 0.5, f"unexpectedly low confidence: {rep['confidence']}"
    return True

if __name__ == '__main__':
    print(main())