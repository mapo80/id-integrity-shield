from PIL import Image
from idtamper.checks import exif, noise


def test_exif_error_branch():
    class Dummy:
        def getexif(self):
            raise ValueError("boom")
    res = exif.run(Dummy())
    assert res["meta"]["error"] == "boom"


def test_noise_blur_branch():
    img = Image.new("RGB", (4, 4), color="white")
    res = noise.run(img, params={"method": "blur", "blur_radius": 1.0})
    assert res["name"] == "noise_inconsistency"
