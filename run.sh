#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

if [ ! -x "$PY" ]; then
  echo "Tworzę venv…"
  python3 -m venv "$VENV"
fi

if ! "$PY" -c "import PIL" 2>/dev/null; then
  echo "Instaluję zależności…"
  "$PIP" install -r requirements.txt
fi

exec "$PY" app.py
