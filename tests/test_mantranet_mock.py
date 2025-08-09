def main():
    from PIL import Image
    import numpy as np
    from idtamper.checks import mantranet
    im = Image.fromarray((np.random.rand(240,360,3)*255).astype('uint8'))
    r = mantranet.run(im, params={"mock": True, "top_percent": 2.0})
    assert r["score"] is not None and 0.0 <= r["score"] <= 1.0
    assert r["map"] is not None
    return True

if __name__=='__main__':
    print(main())