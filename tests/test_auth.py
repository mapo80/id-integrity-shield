
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_missing_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "test_key")
    r = client.get("/protected")
    assert r.status_code == 401

def test_wrong_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "test_key")
    r = client.get("/protected", headers={"x-api-key": "bad"})
    assert r.status_code == 403

def test_ok_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "test_key")
    r = client.get("/protected", headers={"x-api-key": "test_key"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_no_api_key_env(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    r = client.get("/protected")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
