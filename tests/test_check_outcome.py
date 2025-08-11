import os
from fastapi.testclient import TestClient

# ensure profiles and models paths are set
os.environ.setdefault("IDS_PROFILES_DIR", "profiles")
os.environ.setdefault("IDS_MODELS_DIR", ".")
os.environ.setdefault("IDS_MANTRANET_MODEL", "models/mantranet_256x256.onnx")
os.environ.setdefault("IDS_NOISEPRINT_MODEL", "models/noiseprint_pp.onnx")

from app.main import app


def test_check_without_score_has_nd(monkeypatch):
    def fake_analyze(image_path, out_dir, cfg):
        return {
            "per_check": {
                "mantranet": {"score": None, "flag": False},
                "noiseprintpp": {"score": 0.4, "flag": False},
            },
            "threshold": 0.5,
            "is_tampered": False,
            "artifacts": {},
        }
    monkeypatch.setattr("app.main.analyze_image", fake_analyze)
    client = TestClient(app)
    with open("samples/sample1.png", "rb") as f:
        r = client.post("/analyze", files={"file": ("s1.png", f, "image/png")})
    body = r.json()
    assert "mantranet" in body["checks"]
    chk = body["checks"]["mantranet"]
    assert chk.get("score") is None
    assert chk.get("decision") is None
