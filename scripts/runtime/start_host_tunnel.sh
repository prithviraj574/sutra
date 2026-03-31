#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_ENV="$ROOT_DIR/backend/.env"

cd "$ROOT_DIR"

if [[ -f "$BACKEND_ENV" ]]; then
  set -a
  . "$BACKEND_ENV"
  set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-project-3130b11c-429f-49aa-88e}"
ZONE="${GCP_COMPUTE_ZONE:-us-central1-a}"
INSTANCE_NAME="${GCP_RUNTIME_HOST_INSTANCE_NAME:-sutra-firecracker-host}"
HOST_PORT="${GCP_RUNTIME_HOST_API_PORT:-8787}"
LOCAL_HOST_PORT="${SUTRA_RUNTIME_TUNNEL_LOCAL_HOST_PORT:-127.0.0.1:${HOST_PORT}}"

exec gcloud compute start-iap-tunnel \
  "$INSTANCE_NAME" \
  "$HOST_PORT" \
  --project "$PROJECT_ID" \
  --zone "$ZONE" \
  --local-host-port="$LOCAL_HOST_PORT"
