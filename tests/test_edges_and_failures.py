def main():
    from idtamper.checks import noiseprintpp
    from PIL import Image
    import numpy as np

    im = Image.fromarray((np.random.rand(128,192,3)*255).astype('uint8'))

    # deep_onnx removed
    
    
    
    
    
    # noiseprintpp: explicit 'no model' branch (not mock)
    r1 = noiseprintpp.run(im, params={'model_path': None, 'input_size':[256,256]})
    assert r1['score'] is None

    # noiseprintpp: mock with different block size path
    r2 = noiseprintpp.run(im, params={'mock': True, 'input_size':[300,220], 'block': 20, 'score_top_percent':10.0})
    assert r2['score'] is not None and 0.0 <= r2['score'] <= 1.0

    return True

if __name__ == "__main__":
    print(main())