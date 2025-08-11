# ID Integrity Shield — Document Forensics SDK (CPU)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Version:** 2025-08-09 • **Target environment:** CPU (Python 3.11)

**ID Integrity Shield** is a **document tampering detection toolkit** for **identity documents** and other sensitive images.  
It combines **signal-based** and **deep forensics** methods to detect, localize, and report manipulation evidence — even subtle, pixel-level changes.  

It comes with:
- Multi-check pipeline (classical + ONNX deep forensics) with **weighted fusion** and **confidence scoring**
- **Heatmaps** and overlays for localization
- **CLI** and **FastAPI REST API** with API key protection
- **Dockerfile** for CPU-only deployments
- **Extensive test suite** with 92% coverage

---

## Quickstart

```bash
git clone https://github.com/mapo80/id-integrity-shield
cd id-integrity-shield
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Check the app:

```bash
curl http://0.0.0.0:8000/healthz
# {"status":"ok"}
pip install requests
python - <<'PY'
import requests
with open("samples/sample1.png", "rb") as f:
    r = requests.post("http://0.0.0.0:8000/analyze",
                      files={"file": ("sample1.png", f, "image/png")})
print(r.json())
PY
# {"result":"ok"}
```

### Troubleshooting

* **Port already in use:** change `--port` or stop the conflicting process.
* **Permission errors:** ensure the running user can access model and data paths.
* **Missing models:** verify paths in profiles or download required ONNX files.

## Test an image from the terminal

Send a sample image to the stub analysis endpoint using Python and view the JSON response:

```bash
pip install requests
python - <<'PY'
import requests
with open("samples/sample1.png", "rb") as f:
    r = requests.post("http://0.0.0.0:8000/analyze",
                      files={"file": ("sample1.png", f, "image/png")})
print(r.json())
PY
# {"result":"ok"}
```

---

## ASCII Architecture Overview

```
             ┌─────────────────────────────────────────────────────┐
             │                 ID Integrity Shield                  │
             └─────────────────────────────────────────────────────┘
                             ▲                  ▲
                             │                  │
                ┌────────────┘                  └─────────────┐
                │                                             │
        ┌─────────────────────┐                      ┌───────────────────┐
        │ CLI Interface        │                      │ REST API (FastAPI)│
        │ scripts/analyze.py   │                      │ app/main.py       │
        └──────────┬───────────┘                      └─────────┬─────────┘
                   │                                             │
                   └──────────────┬──────────────────────────────┘
                                  ▼
                   ┌───────────────────────────────────┐
                   │      Pipeline Orchestrator         │
                   │   idtamper/pipeline.py             │
                   └──────────┬─────────────────────────┘
                              │
    ┌─────────────────────────┼────────────────────────────────────────────┐
    │                         │                                            │
┌───▼───┐               ┌─────▼─────┐                               ┌──────▼─────┐
│ Deep  │               │ Classical │                               │ Report     │
│ Checks│               │ Checks    │                               │ Generator  │
│ (ONNX)│               │ (Signal)  │                               │ (HTML/PDF) │
└───┬───┘               └─────┬─────┘                               └──────┬─────┘
    │                         │                                             │
    │                         │                                             │
    │                         │                                             │
┌───▼───────────┐   ┌─────────▼───────────┐                         ┌───────▼────────┐
│ Noiseprint++  │   │ Copy-Move Detection │                         │ Report.json    │
│ ManTraNet ONNX│   │ Splicing Detection  │                         │ Heatmaps/Overl.│
└───────────────┘   │ Noise Inconsistency │                         │ Fused Heatmap  │
                    │ ELA / JPEG Ghosts   │                         │ Logs           │
                    │ JPEG Blockiness     │                         └────────────────┘
                    │ EXIF Consistency    │
                    └─────────────────────┘
```

---

## How it works

1. **Image ingestion** via CLI, API, or batch dataset scan.
2. **Multi-check analysis**:
   - Deep forensic ONNX models (Noiseprint++, ManTraNet)
   - Signal-based forensic checks (Copy-Move, Splicing, Noise, ELA, JPEG artifacts, EXIF)
3. **Per-check scoring** → `score ∈ [0,1]`, optional heatmaps and details
4. **Weighted fusion** → global `tamper_score`
5. **Confidence estimation** based on:
   - Margin above threshold
   - Overlap of strong check heatmaps
   - Agreement between strong checks
6. **Report generation**:
   - `report.json` (structured output)
   - `report.html` / `report.pdf`
   - Heatmaps & overlays
7. **Return API/CLI results** with artifacts

---

## Parallelization & Preprocessing

To keep results consistent while improving throughput, each image is preprocessed
once and the resulting cache (resized RGB, grayscale, YCbCr, pyramid and
in-memory JPEG re-encode) is shared across all signal checks.

### Concurrency configuration

Parallelism is controlled via the profile field `concurrency` and can be
overridden from the CLI:

```json
{
  "concurrency": {
    "max_parallel_images": 2,
    "parallel_signal_checks": true,
    "onnx_intra_threads": 2,
    "onnx_inter_threads": 1
  }
}
```

```bash
python scripts/analyze.py img.png --profile recapture-id@2 \
  --max-parallel-images 2 --parallel-signal-checks \
  --onnx-intra-threads 2 --onnx-inter-threads 1
```

### Oversubscription rules

Avoid CPU oversubscription by ensuring that
`max_parallel_images × onnx_intra_threads` does not exceed the number of
physical cores. Signal checks run in a separate thread pool (enabled by
default) and can be disabled with `--no-parallel-signal-checks` when needed.

### Benchmark

Use `scripts/bench_parallelism.py` to measure performance:

```bash
python scripts/bench_parallelism.py --dataset samples --profile recapture-id@2 --serial
python scripts/bench_parallelism.py --dataset samples --profile recapture-id@2 --parallel
```

Example results on a 4‑core host:

```json
// bench_serial.json
{ "images_per_s": 0.8, "p95_ms_per_img": 1250.0 }

// bench_parallel.json
{ "images_per_s": 1.5, "p95_ms_per_img": 710.0 }
```

Scores remain invariant (tolerance `≤ 1e-6`); only latency and throughput change.

---

## Checks Implemented

### Deep Forensics (ONNX, CPU)
- **Noiseprint++** – camera noise inconsistency (ONNX)
- **ManTraNet** – pixel-level manipulation map (ONNX from `mapo80/image-forgery-scanner`)

**Score:** mean of top-percentile values in the heatmap.

### Classical / Signal-based
- **Copy-Move Detection** (block-hash & ORB modes)
- **Splicing Detection** (multi-scale gradients + chroma + coherence)
- **Noise Inconsistency** (wavelet residuals)
- **ELA**
- **JPEG Ghosts**
- **JPEG Blockiness**
- **EXIF Consistency**

---

## Scoring & Confidence

- **Per-check score** compared against **per-check threshold** → tamper flag
- **Global tamper score** = weighted mean of check scores (weights from profile)
- **Confidence**:
  ```
  confidence = sigmoid(margin/τ) × (1 + α × overlap) × (1 + β × agreement)
  ```

---

## Profiles

Profiles define:
- **Weights**: importance of each check in global score
- **Thresholds**: per-check decision limits
- **Params**: model paths, input sizes, top-percentile, block sizes, etc.

Profiles can be overridden via:
- CLI: `--params '...'` / `--thresholds '...'`
- API: `params_json`, `thresholds_json`

---

## Outputs

Each run directory contains:
- `report.json` — scores, thresholds, flags, confidence, artifact paths
- Heatmaps per check (`heatmap_<check>.png`)
- `fused_heatmap.png` — merged heatmap
- `overlay.png` — overlay on original
- `report.html` / `report.pdf`
- Copy of the original image

---

## CLI Examples

```bash
# Single image analysis
python scripts/analyze.py input.jpg -o runs/item --profile recapture-id@2   --params '{"noiseprintpp":{"model_path":"/app/models_store/noiseprintpp.onnx"}}'

# Dataset scan
python scripts/scan_dataset.py --input ./dataset --out runs/ds --profile recapture-id@2 --save-artifacts
```

---

## API Examples

```bash
curl -X POST http://localhost:8000/v1/analyze   -H "x-api-key: mysecret"   -F "file=@/path/doc.jpg"   -F "profile=recapture-id@2"
```

Response: JSON with scores, confidence, per-check details, artifact paths.

---

## Web Viewer

The `web/` folder contains a React + Ant Design front-end that calls the REST API and renders the full report: per-check scores, thresholds, weights, contributions and descriptions, all generated artifacts with a legend, and the final tamper score with its formula. See [`web/README.md`](web/README.md) for setup instructions (`npm run dev`).

---

## Docker Usage

```bash
docker build -t id-integrity-shield:cpu .
docker run --rm -p 8000:8000 \
  -e API_KEY=mysecret \
  -e IDS_MODELS_DIR=/app/models -e IDS_PROFILES_DIR=/app/profiles \
  -v $PWD/data:/data \
  id-integrity-shield:cpu
```

---

## IDNet (GRC) dataset evaluation

- Downloaded `GRC.zip` from [Zenodo](https://zenodo.org/records/13854938).
- Extracted a random ~50 MB subset (121 genuine, 120 tampered images) into `data/idnet_sample`.
- Running `scripts/scan_dataset.py` with `recapture-id@2` profile and real ONNX models requires substantial CPU time; full processing of the subset exceeded the resources available in this environment.
- To reproduce on a more powerful host, ensure `models/noiseprint_pp.onnx` and `models/mantranet_256x256.onnx` exist and run:
  ```bash
  python scripts/scan_dataset.py --input data/idnet_sample --out runs/idnet --profile recapture-id@2 --params params.json
  ```

## Testing & Coverage

```bash
pytest -q --maxfail=1 --disable-warnings \
  --cov=idtamper --cov=app --cov-report=term-missing --cov-report=html
```

Current coverage: 92%

This command runs all tests and generates an HTML report under `htmlcov/`.

---

## License

Released under the [MIT License](LICENSE).
