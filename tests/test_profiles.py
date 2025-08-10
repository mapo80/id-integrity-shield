from idtamper.profiles import load_profile
from pathlib import Path
import json

def test_load_profile_by_name():
    prof = load_profile("recapture-id")
    assert "threshold" in prof


def test_load_profile_from_path(tmp_path):
    data = {"threshold": 0.5, "params": {}, "thresholds": {}, "weights": {}}
    p = tmp_path / "custom.json"
    p.write_text(json.dumps(data))
    prof = load_profile(str(p))
    assert prof["threshold"] == 0.5
