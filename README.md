# ID Integrity Shield — Document Forensics SDK (CPU)

**Version:** 2025-08-09 • **Target environment:** CPU (Python 3.11)

**ID Integrity Shield** is a **document tampering detection toolkit** for **identity documents** and other sensitive images.  
It combines **signal-based** and **deep forensics** methods to detect, localize, and report manipulation evidence — even subtle, pixel-level changes.  

It comes with:
- Multi-check pipeline (classical + ONNX deep forensics) with **weighted fusion** and **confidence scoring**
- **Heatmaps** and overlays for localization
- **CLI** and **FastAPI REST API** with API key protection
- **Dockerfile** for CPU-only deployments
- **Extensive test suite** with >80% coverage

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
│ TruFor ONNX   │   │ Copy-Move Detection │                         │ Report.json    │
│ Noiseprint++  │   │ Splicing Detection  │                         │ Heatmaps/Overl.│
│ ManTraNet ONNX│   │ Noise Inconsistency │                         │ Fused Heatmap  │
└───────────────┘   │ ELA / JPEG Ghosts   │                         │ Logs           │
                    │ JPEG Blockiness     │                         └────────────────┘
                    │ EXIF Consistency    │
                    └─────────────────────┘
```

---

## How it works

1. **Image ingestion** via CLI, API, or batch dataset scan.
2. **Multi-check analysis**:
   - Deep forensic ONNX models (TruFor, Noiseprint++, ManTraNet)
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

## Checks Implemented

### Deep Forensics (ONNX, CPU)
- **TruFor** – manipulation heatmap (ONNX from `mapo80/TruFor`)
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
python scripts/analyze.py input.jpg -o runs/item --profile recapture-id   --params '{"trufor":{"model_path":"/app/models_store/trufor_480x480_op13.onnx"}}'

# Dataset scan
python scripts/scan_dataset.py --input ./dataset --out runs/ds --profile recapture-id --save-artifacts
```

---

## API Examples

```bash
curl -X POST http://localhost:8000/v1/analyze   -H "x-api-key: mysecret"   -F "file=@/path/doc.jpg"   -F "profile=recapture-id"
```

Response: JSON with scores, confidence, per-check details, artifact paths.

---

## Docker Usage

```bash
docker build -t id-integrity-shield:cpu .
docker run --rm -p 8000:8000   -e API_KEY=mysecret   -v $PWD/data:/data   id-integrity-shield:cpu
```

---

## Testing & Coverage

```bash
PYTHONPATH=./idtamper python tests/run_coverage.py
```

This command executes the full test suite and reports code coverage.
The latest run yielded an overall coverage of **69.66%**.
