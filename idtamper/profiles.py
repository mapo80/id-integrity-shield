import os
import json
from pathlib import Path
from typing import Any, Dict

# Directory dei profili configurabile (default: /app/profiles in container)
PROFILES_DIR = Path(os.getenv("IDS_PROFILES_DIR", "/app/profiles"))

def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def load_profile(name_or_path: str) -> Dict[str, Any]:
    """
    Loader robusto dei profili:
      - Accetta path assoluto/relativo o solo nome (con/senza .json)
      - Supporta alias con suffisso '@N' → fallback al core (es. recapture-id@2 → recapture-id)
      - Directory configurabile via env IDS_PROFILES_DIR
    """
    p = Path(name_or_path)

    # 1) Path esplicito
    if p.suffix == ".json" and p.exists():
        return _read_json(p)
    if p.is_absolute() and p.exists():
        return _read_json(p)

    # 2) Nome dentro la dir profili
    stem = p.name[:-5] if p.name.endswith(".json") else p.name
    cand = PROFILES_DIR / f"{stem}.json"
    if cand.exists():
        return _read_json(cand)

    # 3) Fallback alias (recapture-id@2 → recapture-id)
    core = stem.split("@", 1)[0]
    core_cand = PROFILES_DIR / f"{core}.json"
    if core and core_cand.exists():
        return _read_json(core_cand)

    # 4) Errore con elenco disponibili
    available = sorted(x.name for x in PROFILES_DIR.glob("*.json"))
    raise FileNotFoundError(
        f"Profile '{name_or_path}' not found. Looked in {PROFILES_DIR}. Available: {available}"
    )
