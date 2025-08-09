# AGENTS Instructions

## Setup
- Requires Python 3.11.
- Install dependencies with `pip install -r requirements.txt`.
- For a containerized environment, build using the provided Dockerfile.

## Build
- Build Docker image: `docker build -t id-integrity-shield:cpu .`.
- Run the image: `docker run --rm -p 8000:8000 -e API_KEY=mysecret -v $PWD/data:/data id-integrity-shield:cpu`.

## Testing
- Run coverage-based tests: `PYTHONPATH=./idtamper python tests/run_coverage.py`.
- Results are printed as `COVERAGE: <pct>%` and written to `runs/cov/summary.txt`.
- Ensure tests pass before committing changes.
