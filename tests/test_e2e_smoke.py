import os
from fastapi.testclient import TestClient

# ensure profiles and models are found
os.environ.setdefault("IDS_PROFILES_DIR", "profiles")
os.environ.setdefault("IDS_MODELS_DIR", ".")
os.environ.setdefault("IDS_MANTRANET_MODEL", "models/mantranet_256x256.onnx")
os.environ.setdefault("IDS_NOISEPRINT_MODEL", "models/noiseprint_pp.onnx")

from app.main import app


def test_e2e_smoke():
    client = TestClient(app)
    with open("samples/sample1.png", "rb") as f:
        r = client.post("/analyze", files={"file": ("s1.png", f, "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body
    assert "artifacts" in body

    run_id = body["run_id"]

    # ensure top-level artifacts point to the run directory and are reachable
    assert body["artifacts"], "expected at least one artifact"
    first_art = next(iter(body["artifacts"].values()))
    assert f"/runs/{run_id}/" in first_art
    res = client.get(first_art)
    assert res.status_code == 200

    # check-level artifacts, if any, should also contain run_id
    for chk in body.get("checks", {}).values():
        for url in (chk.get("artifacts") or {}).values():
            assert f"/runs/{run_id}/" in url
