#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_ENV="$ROOT_DIR/backend/.env"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
UVICORN_BIN="$BACKEND_DIR/.venv/bin/uvicorn"

load_env_file() {
  local env_file="$1"
  local line
  local key
  local value

  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      ''|\#*)
        continue
        ;;
    esac

    key="${line%%=*}"
    value="${line#*=}"
    export "$key=$value"
  done < "$env_file"
}

if [[ ! -f "$BACKEND_ENV" ]]; then
  echo "Missing backend env file: $BACKEND_ENV" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" || ! -x "$UVICORN_BIN" ]]; then
  echo "Missing backend virtualenv. Expected executables at $PYTHON_BIN and $UVICORN_BIN" >&2
  exit 1
fi

cd "$ROOT_DIR"
load_env_file "$BACKEND_ENV"

if [[ -z "${POSTGRES_URL:-}" ]]; then
  echo "backend/.env must define POSTGRES_URL" >&2
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
exec "$UVICORN_BIN" sutra_backend.main:app --host 127.0.0.1 --port 8000
