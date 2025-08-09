def main():
    from pathlib import Path
    from idtamper.pipeline import analyze_image, AnalyzerConfig
    from idtamper.profiles import load_profile
    from PIL import Image, ImageDraw

    tmp = Path('/mnt/data/idtamper/tmp_trufor'); tmp.mkdir(parents=True, exist_ok=True)
    img = tmp/'doc.png'
    im = Image.new('RGB',(640,400),'white'); dr = ImageDraw.Draw(im)
    dr.rectangle([180,120,460,280], outline='black', width=6); dr.text((200,150),'ID CARD', fill='black')
    im.save(img)

    prof = load_profile('recapture-id')
    params = prof['params']; params['trufor'] = {**params['trufor'], 'mock': True}
    cfg = AnalyzerConfig(weights=prof['weights'], threshold=prof['threshold'], check_params=params, check_thresholds=prof['thresholds'])
    rep = analyze_image(str(img), str(tmp/'out'), cfg)
    assert 'trufor' in rep['per_check']
    assert rep['per_check']['trufor']['score'] is not None
    assert rep['artifacts'].get('heatmap_trufor') is not None
    print('OK trufor', rep['per_check']['trufor']['score'])
    return True

if __name__ == "__main__":
    print(main())