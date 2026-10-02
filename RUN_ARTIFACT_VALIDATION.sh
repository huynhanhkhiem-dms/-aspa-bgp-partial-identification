#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/code${PYTHONPATH:+:$PYTHONPATH}"
python "$ROOT/code/validate_reported_results.py"
python -m pytest -q "$ROOT/tests"
python -m py_compile "$ROOT"/code/*.py "$ROOT"/tests/*.py "$ROOT"/conftest.py
printf 'TECHNICAL_QA=PASS\n'
printf 'ARTIFACT_VALIDATION=PASS\n'
