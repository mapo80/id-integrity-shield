def main():
    from pathlib import Path
    from idtamper.pipeline import analyze_image, AnalyzerConfig
    from idtamper.profiles import load_profile
    from idtamper.report import make_html, make_pdf
    from PIL import Image, ImageDraw

    tmp = Path('/mnt/data/idtamper/tmp_report'); tmp.mkdir(parents=True, exist_ok=True)
    img = tmp/'doc.png'
    im = Image.new('RGB',(512,320),'white')
    dr = ImageDraw.Draw(im); dr.rectangle([120,80,392,240], outline='black', width=5); dr.text((140,120),'ID 123456', fill='black')
    im.save(img)

    prof = load_profile('recapture-id')
    params = prof['params']
    # Use mocks for ONNX to speed up
    params['noiseprintpp'] = {**params['noiseprintpp'], 'mock': True, 'input_size':[256,256]}
    cfg = AnalyzerConfig(weights=prof['weights'], threshold=prof['threshold'], check_params=params, check_thresholds=prof['thresholds'])

    out = tmp/'item'; out.mkdir(exist_ok=True, parents=True)
    # Run analysis & report
    rep = analyze_image(str(img), str(out), cfg)
    html = make_html(out)
    assert Path(html).exists()
    # Attempt PDF (optional)
    pdf, err = make_pdf(out)
    if pdf is None:
        print("PDF skipped:", err)
    else:
        assert Path(pdf).exists()
    return True

if __name__=='__main__':
    print(main())