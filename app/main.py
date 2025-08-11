from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import os, uuid, json, logging, time
from pathlib import Path
from typing import Optional, Dict, Any

from prometheus_fastapi_instrumentator import Instrumentator
from idtamper.pipeline import analyze_image, AnalyzerConfig
from idtamper.profiles import load_profile

API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# ----- Path dati e modelli (configurabili via env) -----
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
INCOMING_DIR = DATA_DIR / "incoming"
RUNS_DIR = DATA_DIR / "runs"
MODELS_DIR = Path(os.getenv("IDS_MODELS_DIR", "/app/models"))
for _d in (INCOMING_DIR, RUNS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

def get_api_key(api_key: str = Depends(api_key_header)):
    expected = os.environ.get("API_KEY")
    if not expected:
        # se non impostata, disabilita auth in dev
        return None
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if api_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    return api_key

app = FastAPI(
    title="ID Integrity Shield",
    version=os.getenv("APP_VERSION", "0.1.0"),
    description="API for document tamper checks (recapture, reprint, splice...).",
    contact={"name": "Maintainers", "url": "https://github.com/mapo80/id-integrity-shield"},
)

logger = logging.getLogger("idshield")
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s path=%(path)s method=%(method)s status=%(status)s duration_ms=%(duration_ms)s msg=%(message)s"
    )
)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    dur = (time.time() - start) * 1000
    logger.info(
        "request",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status": response.status_code,
            "duration_ms": round(dur, 2),
        },
    )
    return response

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "git": os.getenv("GIT_SHA", "unknown"),
    }

@app.post("/analyze")
async def analyze_stub(file: UploadFile = File(...)):
    return {"result": "ok"}

@app.get("/protected")
def protected(_api_key: str = Depends(get_api_key)):
    return {"ok": True}

class AnalyzeResponse(BaseModel):
    image: str
    tamper_score: float
    threshold: float
    is_tampered: bool
    confidence: float
    per_check: Dict[str, Any]
    artifacts: Dict[str, str]

# --- registry modelli interno all’app (profili NON devono contenere i path) ---
# puoi personalizzare via env:
#   IDS_MODELS_DIR
#   IDS_MANTRANET_MODEL
#   IDS_NOISEPRINT_MODEL
DEFAULT_MODEL_REGISTRY = {
    "mantranet":   os.getenv("IDS_MANTRANET_MODEL",   str(MODELS_DIR / "mantranet_256x256.onnx")),
    "noiseprintpp":os.getenv("IDS_NOISEPRINT_MODEL",  str(MODELS_DIR / "noiseprint_pp.onnx")),
}

def _resolve_model_path(model_path: Optional[str]) -> Optional[str]:
    if not model_path:
        return None
    p = Path(model_path)
    return str(p if p.is_absolute() else MODELS_DIR / p)

@app.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(
    file: UploadFile = File(...),
    profile: str = Form("recapture-id@2"),
    out_dir: Optional[str] = Form(None),
    params_json: Optional[str] = Form(None),
    thresholds_json: Optional[str] = Form(None),
    save_artifacts: bool = Form(True),
    _api_key: str = Depends(get_api_key)
):
    # --- salva upload in path scrivibile ---
    item_id = str(uuid.uuid4())[:8]
    img_path = INCOMING_DIR / f"{item_id}_{file.filename}"
    with img_path.open("wb") as f:
        f.write(await file.read())

    prof = load_profile(profile)

    # ----- Params: base profilo + override da form -----
    params: Dict[str, Any] = dict(prof.get("params", {}))
    if params_json:
        user_params = json.loads(params_json)
        for k, v in user_params.items():
            params[k] = {**params.get(k, {}), **v} if isinstance(v, dict) else v

    # ----- Checks dal profilo -----
    checks = prof.get("checks", {})

    # ----- Inietta i path dei modelli (se mancanti) per i check abilitati -----
    for check_name, default_path in DEFAULT_MODEL_REGISTRY.items():
        chk_cfg = checks.get(check_name)
        if not (isinstance(chk_cfg, dict) and chk_cfg.get("enabled")):
            continue
        params.setdefault(check_name, {})
        params[check_name].setdefault("model_path", default_path)
        params[check_name]["model_path"] = _resolve_model_path(params[check_name]["model_path"])
        mp = Path(params[check_name]["model_path"])
        if not mp.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Model for '{check_name}' not found at {mp}. "
                       f"Configure env IDS_MODELS_DIR or IDS_*_MODEL, or mount the file."
            )

    # ----- Thresholds: se mancano nel profilo, derivali dai checks -----
    if "thresholds" in prof and isinstance(prof["thresholds"], dict):
        thresholds: Dict[str, float] = dict(prof["thresholds"])
    else:
        thresholds = {
            name: (cfg.get("threshold", 0.5) if isinstance(cfg, dict) else 0.5)
            for name, cfg in checks.items() if isinstance(cfg, dict)
        }
    if thresholds_json:
        thr_user = json.loads(thresholds_json)
        thresholds.update(thr_user)

    # ----- Threshold globale: supporta prof.decision.threshold o prof.threshold (legacy) -----
    decision = prof.get("decision") or {}
    global_threshold = decision.get("threshold", prof.get("threshold", 0.5))

    # ----- Pesi dei check per l'aggregazione -----
    weights = {
        name: (cfg.get("weight", 0.0) if isinstance(cfg, dict) else 0.0)
        for name, cfg in checks.items() if isinstance(cfg, dict)
    }

    # ----- Verifica che almeno un modello ONNX principale sia abilitato -----
    main_model = None
    for cand in ("mantranet", "noiseprintpp"):
        if cand in checks and checks[cand].get("enabled"):
            main_model = params.get(cand, {}).get("model_path")
            if main_model:
                break
    if not main_model:
        raise HTTPException(
            status_code=500,
            detail="No main ONNX model resolved (expected 'mantranet' or 'noiseprintpp' enabled in profile).",
        )

    cfg = AnalyzerConfig(
        weights=weights,
        threshold=global_threshold,
        check_params=params,
        check_thresholds=thresholds
    )

    out = Path(out_dir) if out_dir else RUNS_DIR / item_id
    out.mkdir(parents=True, exist_ok=True)
    rep = analyze_image(str(img_path), str(out), cfg)

    if not save_artifacts:
        rep["artifacts"] = {}
    return JSONResponse(rep)

@app.get("/v1/health")
def health():
    return {"ok": True}

# simple endpoint to download an artifact if needed
@app.get("/v1/artifact")
def artifact(path: str, _api_key: str = Depends(get_api_key)) -> FileResponse:
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(p))

# ---- SPA static ----
from fastapi.responses import FileResponse as _FileResponse  # evita shadowing
from starlette.staticfiles import StaticFiles

STATIC_DIR = Path("static")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return _FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return _FileResponse(candidate)
        return _FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def serve_index_missing():
        raise HTTPException(status_code=404, detail="Not found")
