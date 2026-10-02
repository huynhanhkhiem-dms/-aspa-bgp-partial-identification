#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python "$ROOT/code/run_full_artifact_validation.py"
