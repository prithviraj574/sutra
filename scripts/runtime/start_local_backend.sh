#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_common.sh"

ROOT_DIR="$(runtime_root_dir "$SCRIPT_DIR")"
BACKEND_ENV="$ROOT_DIR/backend/.env"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
UVICORN_BIN="$BACKEND_DIR/.venv/bin/uvicorn"
BACKEND_HOST="${SUTRA_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${SUTRA_BACKEND_PORT:-8001}"

if [ ! -f "$BACKEND_ENV" ]; then
  echo "Missing backend env file: $BACKEND_ENV" >&2
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ] || [ ! -x "$UVICORN_BIN" ]; then
  echo "Missing backend virtualenv. Expected executables at $PYTHON_BIN and $UVICORN_BIN" >&2
  exit 1
fi

cd "$ROOT_DIR"
load_env_file "$BACKEND_ENV"

if [ -z "${POSTGRES_URL:-}" ]; then
  echo "backend/.env must define POSTGRES_URL" >&2
  exit 1
fi

if [ "${SUTRA_RUNTIME_PROVIDER:-static_dev}" = "static_dev" ] && [ -z "${SUTRA_DEV_RUNTIME_BASE_URL:-}" ]; then
  echo "backend/.env must define SUTRA_DEV_RUNTIME_BASE_URL when SUTRA_RUNTIME_PROVIDER=static_dev" >&2
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

engine = create_database_engine(os.environ["POSTGRES_URL"])
SQLModel.metadata.create_all(engine)
PY

cd "$BACKEND_DIR"
exec "$UVICORN_BIN" sutra_backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload
