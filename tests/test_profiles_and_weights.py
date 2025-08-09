def main():
    from idtamper.profiles import load_profile
    from idtamper.pipeline import AnalyzerConfig, analyze_image
    from PIL import Image
    from pathlib import Path

    # load by name
    prof = load_profile('recapture-id')
    assert 'weights' in prof and 'params' in prof

    # load by path
    ppath = Path('/mnt/data/idtamper/profiles/recapture-id.json')
    prof2 = load_profile(str(ppath))
    assert prof2['threshold'] == prof['threshold']

    # override weights/thresholds/params and run
    im = Image.new('RGB', (120,90), 'white')
    params = prof['params']
    params['trufor'] = {**params['trufor'], 'mock': True}
    cfg = AnalyzerConfig(weights=prof['weights'], threshold=0.25, check_params=params, check_thresholds=prof['thresholds'])
    out = Path('/mnt/data/idtamper/tmp_prof'); out.mkdir(parents=True, exist_ok=True)
    test_img = out/'dummy.png'; im.save(test_img)
    rep = analyze_image(str(test_img), str(out/'o'), cfg)
    assert 'tamper_score' in rep and isinstance(rep['tamper_score'], float)
    return True

if __name__ == "__main__":
    print(main())