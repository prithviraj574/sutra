#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_ID="project-3130b11c-429f-49aa-88e"
ZONE="us-central1-a"
INSTANCE_NAME="sutra-firecracker-host"
LOCAL_HOST_PORT="127.0.0.1:8787"

cd "$ROOT_DIR"

exec gcloud compute start-iap-tunnel \
  "$INSTANCE_NAME" \
  8787 \
  --project "$PROJECT_ID" \
  --zone "$ZONE" \
  --local-host-port="$LOCAL_HOST_PORT"
