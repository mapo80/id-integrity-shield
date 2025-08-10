from pathlib import Path
import pytest

from idtamper.pipeline import analyze_images, AnalyzerConfig
from idtamper.execution import ParallelConfig


def test_serial_vs_parallel(tmp_path):
    imgs = sorted(str(p) for p in Path("samples").glob("*.png"))
    cfg = AnalyzerConfig()
    serial_dir = tmp_path / "serial"
    parallel_dir = tmp_path / "parallel"

    reports_s = analyze_images(
        imgs,
        str(serial_dir),
        cfg,
        ParallelConfig(max_parallel_images=1, parallel_signal_checks=True),
    )
    reports_p = analyze_images(
        imgs,
        str(parallel_dir),
        cfg,
        ParallelConfig(max_parallel_images=2, parallel_signal_checks=True),
    )

    assert len(reports_s) == len(reports_p)
    for rs, rp in zip(reports_s, reports_p):
        assert rs["tamper_score"] == pytest.approx(rp["tamper_score"], abs=1e-6)
        for name, chk in rs["per_check"].items():
            sc = chk["score"]
            pc = rp["per_check"][name]["score"]
            if sc is None and pc is None:
                continue
            assert sc == pytest.approx(pc, abs=1e-6)


def test_parallel_stability(tmp_path):
    imgs = [str(Path("samples/sample1.png")), str(Path("samples/sample2.png"))]
    cfg = AnalyzerConfig()
    pcfg = ParallelConfig(max_parallel_images=2, parallel_signal_checks=True)
    base = analyze_images(imgs, str(tmp_path / "run0"), cfg, pcfg)
    for i in range(1, 3):
        rep = analyze_images(imgs, str(tmp_path / f"run{i}"), cfg, pcfg)
        for r0, r1 in zip(base, rep):
            assert r0["tamper_score"] == pytest.approx(r1["tamper_score"], abs=1e-6)
            for name in r0["per_check"]:
                s0 = r0["per_check"][name]["score"]
                s1 = r1["per_check"][name]["score"]
                if s0 is None and s1 is None:
                    continue
                assert s0 == pytest.approx(s1, abs=1e-6)


def test_metrics_present(tmp_path):
    img = str(Path("samples/sample1.png"))
    cfg = AnalyzerConfig()
    rep = analyze_images([img], str(tmp_path), cfg, ParallelConfig())[0]
    assert rep["metrics"]["total_ms"] >= 0
    assert isinstance(rep["metrics"]["checks"], list) and rep["metrics"]["checks"]
    assert "parallel_config" in rep.get("runtime", {})
