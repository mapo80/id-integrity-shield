# ID Integrity Shield — Viewer (React + Vite + Ant Design)

Un'app leggera per vedere in azione lo SDK: carichi **una sola immagine**, avvii l'analisi, e visualizzi **verdetto**, **punteggi/soglie**, **heatmap/overlay** e una **descrizione testuale**.

## Requisiti
- Node.js 18+
- Endpoint API dello SDK attivo (es. FastAPI su `http://localhost:8000` con endpoint `POST /v1/analyze` che accetta `file`, `profile`, `params`).

## Setup
```bash
npm i
# oppure pnpm i / yarn
```

Crea un file `.env` nella root e imposta:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_API_KEY=la_tua_api_key   # opzionale
VITE_DEFAULT_PROFILE=recapture-id@2
# VITE_PROXY_API=1 # opzionale: proxy locale /v1 -> VITE_API_BASE_URL in dev
```

## Dev
```bash
npm run dev
```

## Build
```bash
npm run build
npm run preview
```

## Note schema output
L'app si adatta a uno schema generico del report:
```jsonc
{
  "profile_id": "recapture-id@2",
  "tamper_score": 0.61,
  "confidence": 0.88,
  "decision": { "threshold": 0.62, "verdict": true },
  "checks": {
    "mantranet":    { "score": 0.58, "threshold": 0.55, "weight": 0.50, "decision": true, "artifacts": {"heatmap":"...","overlay":"..."} },
    "jpeg_ghost":   { "score": 0.66, "threshold": 0.58, "weight": 0.20, "decision": true, "artifacts": {"heatmap":"..."} },
    "ela":          { "score": 0.60, "threshold": 0.60, "weight": 0.20, "decision": true },
    "blockiness":   { "score": 0.51, "threshold": 0.60, "weight": 0.07, "decision": false }
  },
  "artifacts": { "heatmap":"...", "overlay":"..." },
  "metrics": { "total_ms": 740, "checks":[{"name":"ela","ms":22}] },
  "runtime": { "parallel_config": {...}, "hw": {...} }
}
```

Le chiavi `heatmap`/`overlay` possono essere URL assoluti oppure percorsi; se il percorso inizia con `/`, l'app lo risolve rispetto a `VITE_API_BASE_URL`.

## UI
- **Dropzone (singolo file)** con Upload.Dragger
- **Loader** (Spin) durante l'analisi
- **Verdetto + progress** del tamper score
- **Tab visuali**: originale | heatmap/overlay (preview-group)
- **Tabella dettagli** per check (score, soglia, peso, decisione)
- **Descrizione testuale** autogenerata
