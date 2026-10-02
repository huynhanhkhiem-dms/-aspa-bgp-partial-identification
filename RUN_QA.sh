#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/code${PYTHONPATH:+:$PYTHONPATH}"
python -m pytest -q "$ROOT/tests"
python -m py_compile "$ROOT"/code/*.py "$ROOT"/tests/*.py
find "$ROOT" -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
printf 'TECHNICAL_QA=PASS\n'
