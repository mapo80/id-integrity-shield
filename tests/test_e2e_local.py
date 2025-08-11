import io, os, json, importlib, pathlib
from typing import Optional
import pytest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
MODELS = pathlib.Path(os.getenv("IDS_MODELS_DIR", ROOT / "models"))
PROFILES = pathlib.Path(os.getenv("IDS_PROFILES_DIR", ROOT / "profiles"))
SAMPLES = ROOT / "samples"

def _resolve_app():
    # prova moduli comuni senza assumere un path fisso
    candidates = ("app.main", "server", "main", "api.main")
    last_err = None
    for mod in candidates:
        try:
            m = importlib.import_module(mod)
            app = getattr(m, "app", None)
            if app is not None:
                return app
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Impossibile importare FastAPI app. Provati {candidates}. Ultimo errore: {last_err}")

def _pick_model(patterns):
    for p in MODELS.glob("*.onnx"):
        name = p.name.lower()
        if any(x in name for x in patterns):
            return p
    return None

def test_models_and_profiles_present():
    assert MODELS.exists(), "La cartella models/ deve esistere"
    assert any(MODELS.glob("*.onnx")), "Nessun modello .onnx trovato in models/"
    assert PROFILES.exists(), "La cartella profiles/ deve esistere"
    assert any(PROFILES.glob("*.json")), "Nessun profilo .json trovato"

def test_sample_available():
    samp = next(iter(SAMPLES.glob("**/*.*")), None)
    assert samp is not None, "Nessun file di test in samples/"

def test_api_analyze_end2end():
    app = _resolve_app()
    try:
        from fastapi.testclient import TestClient
    except Exception as e:
        pytest.skip(f"fastapi.testclient mancante: {e}")
    client = TestClient(app)

    # /healthz opzionale
    try:
        r = client.get("/healthz")
        assert r.status_code in (200, 404)
    except Exception:
        pass

    # campioni e modelli
    sample = next(iter(SAMPLES.glob("**/*.*")))
    data = sample.read_bytes()

    noise = _pick_model(("noise", "np", "nprint"))
    mantra = _pick_model(("mantra", "mantranet"))
    assert noise and mantra, f"Modelli non risolti: noise={noise}, mantranet={mantra}"

    params = {
        "noiseprintpp": {"model_path": str(noise)},
        "mantranet": {"model_path": str(mantra)}
    }

    files = {"file": (sample.name, io.BytesIO(data), "image/jpeg")}
    form = {"profile": "recapture-id", "params": json.dumps(params)}
    resp = client.post("/v1/analyze", files=files, data=form)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert ("tamper_score" in body) or ("checks" in body), f"Report incompleto: {body}"

def test_spa_built_or_mounted():
    # se static/index.html esiste, verifichiamo che l'app serva "/" (200)
    static_index = ROOT / "static" / "index.html"
    if not static_index.exists():
        pytest.skip("SPA non buildata: static/index.html non presente")
    app = _resolve_app()
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200, f"Atteso 200 su /, ottenuto {r.status_code}"
