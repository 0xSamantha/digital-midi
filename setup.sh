#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3.11}"
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
