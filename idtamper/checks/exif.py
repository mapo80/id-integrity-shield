def run(pil_image, params=None):
    try:
        exif = pil_image.getexif()
        ok = (exif is not None and len(exif)>0)
        score = 0.0 if ok else 0.5
        return {"name":"exif", "score": score, "map": None, "meta": {"has_exif": ok, "count": len(exif) if exif else 0}}
    except Exception as e:
        return {"name":"exif", "score": 0.5, "map": None, "meta": {"error": str(e)}}