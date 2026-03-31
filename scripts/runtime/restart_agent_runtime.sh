#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <agent-id>" >&2
  exit 1
fi

if [[ -z "${SUTRA_BASE_URL:-}" || -z "${SUTRA_BEARER_TOKEN:-}" ]]; then
  echo "SUTRA_BASE_URL and SUTRA_BEARER_TOKEN are required." >&2
  exit 1
fi

agent_id="$1"

curl -fsS \
  -X POST \
  -H "Authorization: Bearer ${SUTRA_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  "${SUTRA_BASE_URL}/api/agents/${agent_id}/runtime/restart"
