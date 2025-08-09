def main():
    from pathlib import Path
    import numpy as np
    from PIL import Image, ImageFilter
    from idtamper.checks import noise

    # Synthetic: add small pasted-noise area
    arr = (np.ones((240,340))*0.9*255).astype('uint8')
    im = Image.fromarray(arr, 'L').convert('RGB')
    # inject noise patch
    import numpy as _np
    patch = ( (_np.random.rand(60, 80)*255).astype('uint8') )
    im_arr = _np.array(im.convert('L'))
    im_arr[120:180, 200:280] = patch
    im2 = Image.fromarray(im_arr, 'L').convert('RGB')

    res = noise.run(im2, params={'method':'wavelet','block':24,'step':12,'top_percent':5.0})
    assert res['score'] is not None and 0.0 <= res['score'] <= 1.0
    assert res['score'] > 0.10, f"noise wavelet score too low: {res['score']}"
    return True

if __name__=='__main__':
    print(main())