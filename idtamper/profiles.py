import json
from pathlib import Path
def load_profile(name_or_path):
    p = Path(name_or_path)
    if p.exists():
        return json.loads(p.read_text())
    here = Path(__file__).resolve().parents[1]/"profiles"
    return json.loads((here/f"{name_or_path}.json").read_text())