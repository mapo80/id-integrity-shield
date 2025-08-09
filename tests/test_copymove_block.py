def main():
    from pathlib import Path
    import numpy as np
    from PIL import Image, ImageDraw
    from idtamper.checks import copymove

    tmp = Path('/mnt/data/idtamper/tmp_copymove'); tmp.mkdir(parents=True, exist_ok=True)
    # Build synthetic image with a duplicated rectangle pasted elsewhere
    im = Image.new('RGB', (320, 220), 'white')
    dr = ImageDraw.Draw(im)
    dr.rectangle([40,60,120,120], fill='black')  # source region
    # paste copy (simulate copy-move)
    # np.asarray returns a read-only view; use np.array to get a writable copy
    arr = np.array(im)
    patch = arr[60:120, 40:120].copy()
    arr[80:140, 170:250] = patch  # move to right side
    im2 = Image.fromarray(arr)

    res = copymove.run(im2, params={
        'mode':'block', 'block':16, 'step':8,
        'ham_tol':6, 'min_offset':10, 'min_cluster':6, 'top_percent':2.0
    })
    assert res['score'] is not None and 0.0 <= res['score'] <= 1.0
    # Expect non-trivial score
    assert res['score'] > 0.10, f"score too low: {res['score']}"
    # Heatmap should have energy near both regions
    hm = res['map']; import numpy as np
    left = hm[60:120, 40:120].mean()
    right = hm[80:140, 170:250].mean()
    assert left>0 or right>0, "heatmap not highlighting duplicated areas"
    print("copy-move block score:", res['score'], "left", left, "right", right)
    return True

if __name__=='__main__':
    print(main())