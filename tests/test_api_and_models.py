import io, json, os, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
MODELS = ROOT / "models"
PROFILES = ROOT / "profiles"
SAMPLES = ROOT / "samples"

# ensure app uses local models and profiles
os.environ.setdefault("IDS_MODELS_DIR", str(MODELS))
os.environ.setdefault("IDS_PROFILES_DIR", str(PROFILES))

from fastapi.testclient import TestClient
# usa la TUA app FastAPI
from app.main import app

def test_models_exist_and_readable():
    assert MODELS.exists(), "La cartella models/ deve esistere"
    onnx_files = list(MODELS.glob("*.onnx"))
    assert onnx_files, "Nessun modello .onnx trovato in models/"
    # presenza attesa: noiseprint++ e mantranet (nomi flessibili)
    assert any("noise" in f.name.lower() for f in onnx_files), "Modello Noiseprint++ non trovato"
    assert any("mantra" in f.name.lower() or "mantranet" in f.name.lower() for f in onnx_files), "Modello ManTraNet non trovato"

def test_profile_exists():
    assert PROFILES.exists(), "La cartella profiles/ deve esistere"
    profs = list(PROFILES.glob("*.json"))
    assert profs, "Nessun profilo .json trovato"

def test_health_and_root_page():
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    # la home restituisce index.html (SPA) se /app/static presente
    r2 = client.get("/")
    assert r2.status_code in (200, 404)  # 200 quando static/ c'è, 404 se non montata in dev

def test_analyze_endpoint_end2end():
    client = TestClient(app)
    # immagine di test
    sample = next(iter(SAMPLES.glob("**/*.*")), None)
    assert sample is not None, "Nessuna immagine in samples/"
    data = sample.read_bytes()

    # risolvi path modello dentro repo (dev) o via ENV in container
    models_dir = pathlib.Path(os.getenv("IDS_MODELS_DIR", MODELS))
    # pick file by pattern (robusto ai nomi)
    noise = next((p for p in models_dir.glob("*.onnx") if "noise" in p.name.lower()), None)
    mantr = next((p for p in models_dir.glob("*.onnx") if "mantra" in p.name.lower() or "mantranet" in p.name.lower()), None)
    assert noise and mantr, "Modelli noise/mantra non risolti"

    params = {
        "noiseprintpp": {"model_path": str(noise)},
        "mantranet": {"model_path": str(mantr)}
    }

    files = {"file": (sample.name, io.BytesIO(data), "image/jpeg")}
    form = {"profile": "recapture-id@2", "params": json.dumps(params)}
    resp = client.post("/v1/analyze", files=files, data=form)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # campi minimi del report
    assert "tamper_score" in body or "checks" in body, f"Report incompleto: {body}"
