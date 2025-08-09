def main():
    import numpy as np
    from PIL import Image, ImageFilter
    from idtamper.checks import copymove

    im = Image.new('RGB', (320,240), 'white').filter(ImageFilter.GaussianBlur(0.5))
    res = copymove.run(im, params={'mode':'block','block':16,'step':8,'min_cluster':10})
    assert res['score'] is not None and 0.0 <= res['score'] <= 1.0
    # Expect low score on clean image
    assert res['score'] < 0.25, f"unexpected high score on clean image: {res['score']}"
    print("copy-move clean score:", res['score'])
    return True

if __name__=='__main__':
    print(main())