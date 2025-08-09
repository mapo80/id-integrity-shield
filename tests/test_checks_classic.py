def main():
    from pathlib import Path
    import numpy as np
    from PIL import Image, ImageFilter
    from idtamper.checks import ela, jpegghost, noise, blockiness, splicing, exif, copymove

    tmp = Path('/mnt/data/idtamper/tmp_checks'); tmp.mkdir(parents=True, exist_ok=True)
    img = tmp/'img.jpg'
    im = Image.new('RGB', (300,200), 'white')
    im = im.filter(ImageFilter.GaussianBlur(radius=0.2))
    im.save(img)

    # Run all classic checks
    r_ela = ela.run(im, params={'quality':92,'scale':8.0,'top_percent':5.0})
    r_gho = jpegghost.run(im, params={'qualities':[75,85],'top_percent':5.0})
    r_noi = noise.run(im, params={'block':16,'step':8,'blur_radius':1.0,'top_percent':5.0})
    r_blk = blockiness.run(im, params={'q':8})
    r_spl = splicing.run(im, params={'max_side':512})
    r_exf = exif.run(im, params={})
    r_cmv = copymove.run(im, params={})

    for r in (r_ela, r_gho, r_noi, r_blk, r_spl, r_exf, r_cmv):
        assert 'score' in r and 'map' in r
        sc = r['score']
        assert (sc is None) or (0.0 <= sc <= 1.0)
    return True

if __name__ == "__main__":
    print(main())