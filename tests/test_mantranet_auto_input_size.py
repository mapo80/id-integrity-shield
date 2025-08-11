import importlib.util
from pathlib import Path
import numpy as np
from PIL import Image

spec = importlib.util.spec_from_file_location(
    "mantranet", Path(__file__).resolve().parent.parent / "idtamper" / "checks" / "mantranet.py"
)
mantranet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mantranet)

class DummyInput:
    name = 'img_in'
    shape = [1, 3, 256, 256]

class DummySession:
    def get_inputs(self):
        return [DummyInput()]
    def run(self, outs, feeds):
        x = list(feeds.values())[0]
        # ensure we received expected 256x256 tensor
        assert x.shape[-2:] == (256, 256)
        return [np.zeros((1, 1, 256, 256), dtype='float32')]

def test_autodetect_input_size():
    im = Image.fromarray((np.random.rand(512,512,3)*255).astype('uint8'))
    r = mantranet.run(im, params={'session': DummySession()})
    assert r['score'] is not None
    assert r['meta']['input_size'] == [256, 256]
