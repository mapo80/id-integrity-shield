
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import os, shutil, uuid, json, logging, time
from pathlib import Path
from typing import Optional, Dict, Any

from prometheus_fastapi_instrumentator import Instrumentator
from idtamper.pipeline import analyze_image, AnalyzerConfig
from idtamper.profiles import load_profile

API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_api_key(api_key: str = Depends(api_key_header)):
    expected = os.environ.get("API_KEY")
    if not expected:
        # if not set, disable auth for dev
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

@app.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(
    file: UploadFile = File(...),
    profile: str = Form("recapture-id"),
    out_dir: Optional[str] = Form(None),
    params_json: Optional[str] = Form(None),
    thresholds_json: Optional[str] = Form(None),
    save_artifacts: bool = Form(True),
    _api_key: str = Depends(get_api_key)
):
    tmp_root = Path("/data/incoming"); tmp_root.mkdir(parents=True, exist_ok=True)
    item_id = str(uuid.uuid4())[:8]
    img_path = tmp_root / f"{item_id}_{file.filename}"
    with img_path.open("wb") as f:
        f.write(await file.read())

    prof = load_profile(profile)
    params = prof["params"]
    if params_json:
        user_params = json.loads(params_json)
        # shallow merge: override specific trees
        for k,v in user_params.items():
            params[k] = {**params.get(k, {}), **v} if isinstance(v, dict) else v
    thresholds = prof["thresholds"]
    if thresholds_json:
        thr_user = json.loads(thresholds_json)
        thresholds.update(thr_user)

    cfg = AnalyzerConfig(weights=prof["weights"], threshold=prof["threshold"], check_params=params, check_thresholds=thresholds)
    out = Path(out_dir) if out_dir else Path("/data/runs")/item_id
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
