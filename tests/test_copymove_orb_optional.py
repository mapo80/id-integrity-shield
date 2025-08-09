def main():
    try:
        import cv2  # noqa: F401
    except Exception as e:
        print("SKIP ORB test: OpenCV not available:", e)
        return True
    from PIL import Image, ImageDraw
    from idtamper.checks import copymove
    im = Image.new('RGB', (320, 220), 'white')
    dr = ImageDraw.Draw(im)
    dr.rectangle([40,60,120,120], fill='black')
    arr = np.asarray(im)
    patch = arr[60:120, 40:120].copy()
    arr[82:142, 172:252] = patch
    im2 = Image.fromarray(arr)
    res = copymove.run(im2, params={'mode':'orb', 'min_cluster':4})
    assert res['score'] is not None and 0.0 <= res['score'] <= 1.0
    print("copy-move ORB score:", res['score'], res['meta'])
    return True

if __name__=='__main__':
    print(main())