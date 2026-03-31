#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_ENV="$ROOT_DIR/backend/.env"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
UVICORN_BIN="$BACKEND_DIR/.venv/bin/uvicorn"

if [[ ! -f "$BACKEND_ENV" ]]; then
  echo "Missing backend env file: $BACKEND_ENV" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" || ! -x "$UVICORN_BIN" ]]; then
  echo "Missing backend virtualenv. Expected executables at $PYTHON_BIN and $UVICORN_BIN" >&2
  exit 1
fi

cd "$ROOT_DIR"
set -a
. "$BACKEND_ENV"
set +a

if [[ -z "${DATABASE_URL:-}" && -n "${POSTGRES_URL:-}" ]]; then
  export DATABASE_URL="$POSTGRES_URL"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "backend/.env must define DATABASE_URL or POSTGRES_URL" >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import os
import sys

root = Path.cwd()
sys.path.insert(0, str(root / "backend"))

from sqlmodel import SQLModel
from sutra_backend.db import create_database_engine
from sutra_backend.models import *  # noqa: F401,F403

engine = create_database_engine(os.environ["DATABASE_URL"])
SQLModel.metadata.create_all(engine)
PY

cd "$BACKEND_DIR"
exec "$UVICORN_BIN" sutra_backend.main:app --host 127.0.0.1 --port 8000
