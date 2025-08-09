def main():
    import numpy as np
    from idtamper.visualize import fuse_heatmaps, overlay_on_image
    from idtamper.aggregate import fuse_scores, DEFAULT_WEIGHTS
    from PIL import Image
    # fuse heatmaps
    h1 = np.ones((64,64), dtype=float)*0.4
    h2 = np.zeros((64,64), dtype=float)
    hms = {'a': h1, 'b': h2}
    fused = fuse_heatmaps(hms, weights={'a':2.0,'b':1.0})
    assert fused.shape == (64,64)
    # overlay
    img = Image.new('RGB', (128,128), 'white')
    ov = overlay_on_image(img, fused, alpha=0.5)
    assert ov.size == (128,128)
    # fuse scores
    per = {'x': {'score':0.8}, 'y': {'score':0.2}}
    w = {'x':0.75, 'y':0.25}
    sc = fuse_scores(per, w)
    assert 0.0 <= sc <= 1.0 and sc > 0.2
    return True

if __name__ == "__main__":
    print(main())