from idtamper.pipeline import analyze_image, AnalyzerConfig
from pathlib import Path
import json

def test_analyze_image(tmp_path):
    out_dir = tmp_path / "out"
    cfg = AnalyzerConfig()
    report = analyze_image("samples/sample1.png", str(out_dir), cfg)
    assert "tamper_score" in report
    rp = out_dir / "report.json"
    assert rp.exists()
    data = json.loads(rp.read_text())
    assert data["image"] == "sample1.png"
