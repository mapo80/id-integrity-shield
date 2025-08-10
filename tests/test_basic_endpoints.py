
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app

client = TestClient(app)

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_version(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("GIT_SHA", "abc123")
    r = client.get("/version")
    assert r.status_code == 200
    assert r.json() == {"version": "1.2.3", "git": "abc123"}


def test_v1_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_v1_analyze_and_artifact(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY", "secret")

    def fake_analyze_image(img_path, out, cfg):
        out_path = Path(out) / "dummy.txt"
        out_path.write_text("hello")
        return {
            "image": img_path,
            "tamper_score": 0.1,
            "threshold": 0.5,
            "is_tampered": False,
            "confidence": 0.9,
            "per_check": {},
            "artifacts": {"dummy": str(out_path)},
        }

    monkeypatch.setattr("app.main.analyze_image", fake_analyze_image)

    client = TestClient(app)
    with open("samples/sample1.png", "rb") as f:
        r = client.post(
            "/v1/analyze",
            files={"file": ("sample1.png", f, "image/png")},
            headers={"x-api-key": "secret"},
            data={"out_dir": str(tmp_path)},
        )

    assert r.status_code == 200
    data = r.json()
    assert "dummy" in data["artifacts"]
    art_path = data["artifacts"]["dummy"]

    r2 = client.get(f"/v1/artifact?path={art_path}", headers={"x-api-key": "secret"})
    assert r2.status_code == 200
    assert r2.content == b"hello"
