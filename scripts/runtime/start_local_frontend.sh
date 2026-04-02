#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND_HOST="${SUTRA_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${SUTRA_FRONTEND_PORT:-5173}"
BACKEND_HOST="${SUTRA_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${SUTRA_BACKEND_PORT:-8001}"

export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"

cd "$ROOT_DIR/frontend"
exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
