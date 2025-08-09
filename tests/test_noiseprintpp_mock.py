def main():
    from pathlib import Path
    from idtamper.pipeline import analyze_image, AnalyzerConfig
    from idtamper.profiles import load_profile
    from PIL import Image
    import numpy as np

    tmp = Path('/mnt/data/idtamper/tmp_noisepp'); tmp.mkdir(parents=True, exist_ok=True)
    img = tmp/'noisy.png'
    arr = (np.random.rand(500,800,3)*255).astype('uint8'); Image.fromarray(arr).save(img)

    prof = load_profile('recapture-id')
    params = prof['params']; params['noiseprintpp'] = {**params['noiseprintpp'], 'mock': True, 'input_size':[512,512]}
    cfg = AnalyzerConfig(weights=prof['weights'], threshold=prof['threshold'], check_params=params, check_thresholds=prof['thresholds'])
    rep = analyze_image(str(img), str(tmp/'out'), cfg)
    assert 'noiseprintpp' in rep['per_check']
    assert rep['per_check']['noiseprintpp']['score'] is not None
    assert rep['artifacts'].get('heatmap_noiseprintpp') is not None
    print('OK noiseprintpp', rep['per_check']['noiseprintpp']['score'])
    return True

if __name__ == "__main__":
    print(main())