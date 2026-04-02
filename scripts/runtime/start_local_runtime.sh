#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_common.sh"

ROOT_DIR="$(runtime_root_dir "$SCRIPT_DIR")"
BACKEND_ENV="$ROOT_DIR/backend/.env"
HERMES_DIR="$ROOT_DIR/backend/hermes-agent"
HERMES_HOME_DIR="$ROOT_DIR/.local/hermes"

if [ ! -f "$BACKEND_ENV" ]; then
  echo "Missing backend env file: $BACKEND_ENV" >&2
  exit 1
fi

cd "$ROOT_DIR"
load_env_file "$BACKEND_ENV"

mkdir -p "$HERMES_HOME_DIR"

export HERMES_HOME="${SUTRA_LOCAL_HERMES_HOME:-$HERMES_HOME_DIR}"
export API_SERVER_ENABLED="${API_SERVER_ENABLED:-true}"
export API_SERVER_HOST="${API_SERVER_HOST:-127.0.0.1}"
export API_SERVER_PORT="${API_SERVER_PORT:-8642}"
export API_SERVER_KEY="${API_SERVER_KEY:-${SUTRA_RUNTIME_API_KEY:-${SUTRA_DEV_RUNTIME_API_KEY:-}}}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"

if [ -z "${API_SERVER_KEY:-}" ]; then
  echo "backend/.env must define SUTRA_RUNTIME_API_KEY (or SUTRA_DEV_RUNTIME_API_KEY) to start the local runtime." >&2
  exit 1
fi

if [ -z "${SUTRA_DEV_RUNTIME_BASE_URL:-}" ]; then
  export SUTRA_DEV_RUNTIME_BASE_URL="http://${API_SERVER_HOST}:${API_SERVER_PORT}"
fi

cd "$HERMES_DIR"
UV_RUN_ARGS=(--project "$HERMES_DIR")
if [ -n "${HONCHO_API_KEY:-}" ] || [ -n "${HONCHO_BASE_URL:-}" ] || [ -n "${SUTRA_HONCHO_API_KEY:-}" ] || [ -n "${SUTRA_HONCHO_BASE_URL:-}" ]; then
  UV_RUN_ARGS+=(--extra honcho)
fi

exec uv run "${UV_RUN_ARGS[@]}" python -m gateway.run
