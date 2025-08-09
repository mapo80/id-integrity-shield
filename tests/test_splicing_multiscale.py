def main():
    from pathlib import Path
    from PIL import Image, ImageDraw, ImageFilter
    from idtamper.checks import splicing

    # Create synthetic: base + pasted region with different blur (seam)
    im = Image.new('RGB', (360, 260), 'white')
    dr = ImageDraw.Draw(im); dr.rectangle([80,70,220,190], fill=(200,200,200))
    patch = im.crop((80,70,220,190)).filter(ImageFilter.GaussianBlur(1.8))
    im.paste(patch, (110,85))  # offset pasted region
    res = splicing.run(im, params={'mode':'multiscale','scales':[1.0,2.0,4.0],'win':7,'top_percent':1.0})
    assert res['score'] is not None and 0.0 <= res['score'] <= 1.0
    assert res['score'] > 0.10, f"splicing score too low: {res['score']}"
    return True

if __name__=='__main__':
    print(main())