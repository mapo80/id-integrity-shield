
import sys
from pathlib import Path
from trace import Trace

BASE = Path(__file__).resolve().parents[1]
PKG = BASE/'idtamper'
TESTS = BASE/'tests'

def is_countable(line:str):
    s = line.strip()
    return not (s=='' or s.startswith('#'))

def run():
    sys.path.insert(0, str(BASE))
    tracer = Trace(count=True, trace=False)
    for m in TESTS.glob('test_*.py'):
        code = compile(m.read_text(), str(m), 'exec')
        globs = {'__name__': '__main__', '__file__': str(m)}
        tracer.runctx(code, globs, {})
    res = tracer.results()
    counts = res.counts  # (filename, lineno) -> count

    files = [p for p in PKG.rglob('*.py')]
    total_exec = 0; total_lines = 0
    per_file = []
    for f in files:
        try:
            lines = f.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue
        n_countable = sum(1 for ln in lines if is_countable(ln))
        executed = 0
        for i, ln in enumerate(lines, start=1):
            if not is_countable(ln): continue
            if (str(f), i) in counts and counts[(str(f), i)] > 0:
                executed += 1
        total_exec += executed; total_lines += n_countable
        pct = (executed/n_countable*100.0) if n_countable>0 else 0.0
        per_file.append((str(f.relative_to(BASE)), executed, n_countable, pct))

    per_file.sort()
    cov = (total_exec/total_lines*100.0) if total_lines>0 else 0.0
    # write summary
    out = BASE/'runs'/'cov'; out.mkdir(parents=True, exist_ok=True)
    with (out/'summary.txt').open('w') as f:
        f.write(f"Coverage: {cov:.2f}% (covered {total_exec}/{total_lines})\n")
        for rel, ex, tot, pct in per_file:
            f.write(f"{rel}: {pct:.1f}% ({ex}/{tot})\n")
    print(f"COVERAGE: {cov:.2f}%")
    return cov

if __name__ == '__main__':
    print({'coverage_percent': run()})
