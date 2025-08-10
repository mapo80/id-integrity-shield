from fastapi.testclient import TestClient
from app.main import app


def test_e2e_smoke():
    client = TestClient(app)
    with open("samples/sample1.png", "rb") as f:
        r = client.post("/analyze", files={"file": ("s1.png", f, "image/png")})
    assert r.status_code == 200
    assert "result" in r.json()
