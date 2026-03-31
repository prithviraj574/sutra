#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <host-instance-name> [host-disk-name]" >&2
  exit 1
fi

if [[ -z "${GCP_PROJECT_ID:-}" || -z "${GCP_COMPUTE_ZONE:-}" ]]; then
  echo "GCP_PROJECT_ID and GCP_COMPUTE_ZONE are required." >&2
  exit 1
fi

instance_name="$1"
disk_name="${2:-${instance_name}-data}"

gcloud compute instances delete "${instance_name}" \
  --project "${GCP_PROJECT_ID}" \
  --zone "${GCP_COMPUTE_ZONE}" \
  --quiet || true

gcloud compute disks delete "${disk_name}" \
  --project "${GCP_PROJECT_ID}" \
  --zone "${GCP_COMPUTE_ZONE}" \
  --quiet || true
