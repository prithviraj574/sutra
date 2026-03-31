#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_ENV="$ROOT_DIR/.context/local/backend.env"
SQLITE_DB="$ROOT_DIR/.context/local/sutra.sqlite"

if [[ ! -f "$BACKEND_ENV" ]]; then
  echo "Missing backend env file: $BACKEND_ENV" >&2
  exit 1
fi

mkdir -p "$(dirname "$SQLITE_DB")"

cd "$ROOT_DIR"
set -a
source "$BACKEND_ENV"
set +a

./backend/.venv/bin/python - <<'PY'
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

cd "$ROOT_DIR/backend"
exec ./.venv/bin/uvicorn sutra_backend.main:app --host 127.0.0.1 --port 8000
