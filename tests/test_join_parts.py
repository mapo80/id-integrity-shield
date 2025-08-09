def main():
    from pathlib import Path
    import os, subprocess, sys
    tmp = Path('/mnt/data/idtamper/tmp_join'); tmp.mkdir(parents=True, exist_ok=True)
    parts = [tmp/f'model.onnx.part{i}' for i in (1,2,3)]
    data = [os.urandom(1024) for _ in parts]
    for p,d in zip(parts, data): p.write_bytes(d)
    out = tmp/'model.onnx'
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root/'scripts'/'join_parts.py'
    res = subprocess.run([sys.executable, str(script), '--out', str(out), '--parts', *[str(p) for p in parts]], capture_output=True, text=True)
    assert res.returncode==0, res.stderr
    assert out.read_bytes() == b''.join(data)
    print('OK join', out.stat().st_size)
    return True

if __name__ == "__main__":
    print(main())