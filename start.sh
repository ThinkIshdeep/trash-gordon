#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3.12 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
exec .venv/bin/python run.py "$@"
