def main():
    import subprocess, sys
    from pathlib import Path
    from PIL import Image, ImageDraw
    import json, os

    root = Path('/mnt/data/idtamper/tmp_dataset'); 
    tam = root/'fake'; gen = root/'real'
    (tam).mkdir(parents=True, exist_ok=True); (gen).mkdir(parents=True, exist_ok=True)

    def mk(path, txt):
        im = Image.new('RGB', (240,160), 'white')
        dr = ImageDraw.Draw(im); dr.rectangle([40,40,200,120], outline='black', width=4); dr.text((60,60), txt, fill='black')
        im.save(path)

    mk(tam/'a.jpg','A'); mk(tam/'b.jpg','B'); mk(gen/'c.jpg','C')

    params = {
      "trufor": {"mock": True, "input_size":[384,384]},
      "noiseprintpp": {"mock": True, "input_size":[256,256]}
    }
    params_path = root/'params.json'; params_path.write_text(json.dumps(params))

    out = Path('/mnt/data/idtamper/runs/cli_cov'); 
    if out.exists():
        import shutil; shutil.rmtree(out)
    cmd = [sys.executable, '/mnt/data/idtamper/scripts/scan_dataset.py', '--input', str(root), '--out', str(out), '--profile', 'recapture-id', '--params', str(params_path), '--save-artifacts']
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert (out/'dataset_report.csv').exists()
    assert (out/'summary.json').exists()
    # quick sanity check on summary fields
    s = json.loads((out/'summary.json').read_text())
    assert 'precision' in s and 'recall' in s and 'count' in s
    return True

if __name__ == "__main__":
    print(main())