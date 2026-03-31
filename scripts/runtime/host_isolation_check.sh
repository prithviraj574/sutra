#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 5 ]]; then
  echo "usage: $0 <hermes-home-path> <private-volume-path> <shared-workspace-path> [state-mount-path] [sibling-private-root]" >&2
  exit 1
fi

hermes_home="$1"
private_volume="$2"
shared_workspace="$3"
state_mount="${4:-/mnt/sutra/state}"
sibling_private_root="${5:-}"

for path in "$hermes_home" "$private_volume" "$shared_workspace" "$state_mount"; do
  if [[ ! -e "$path" ]]; then
    echo "missing path: $path" >&2
    exit 1
  fi
done

if [[ -L "$hermes_home" || -L "$private_volume" || -L "$shared_workspace" ]]; then
  echo "symlinks are not allowed for runtime storage paths" >&2
  exit 1
fi

if [[ "$hermes_home" == "$private_volume" ]]; then
  echo "HERMES_HOME and private volume must be distinct" >&2
  exit 1
fi

case "$hermes_home" in
  "$shared_workspace"|"$shared_workspace"/*)
    echo "HERMES_HOME must not live inside the shared workspace" >&2
    exit 1
    ;;
esac

case "$private_volume" in
  "$shared_workspace"|"$shared_workspace"/*)
    echo "private volume must not live inside the shared workspace" >&2
    exit 1
    ;;
esac

case "$hermes_home" in
  "$state_mount"|"$state_mount"/*) ;;
  *)
    echo "HERMES_HOME must live under the private state mount" >&2
    exit 1
    ;;
esac

case "$private_volume" in
  "$state_mount"|"$state_mount"/*) ;;
  *)
    echo "private volume must live under the private state mount" >&2
    exit 1
    ;;
esac

hermes_mode="$(stat -f '%Lp' "$hermes_home")"
private_mode="$(stat -f '%Lp' "$private_volume")"

if [[ "$hermes_mode" != "700" ]]; then
  echo "HERMES_HOME permissions must be 700, got $hermes_mode" >&2
  exit 1
fi

if [[ "$private_mode" != "700" ]]; then
  echo "private volume permissions must be 700, got $private_mode" >&2
  exit 1
fi

if [[ -n "$sibling_private_root" ]]; then
  case "$hermes_home" in
    "$sibling_private_root"|"$sibling_private_root"/*)
      echo "HERMES_HOME must not live inside a sibling agent private root" >&2
      exit 1
      ;;
  esac

  case "$private_volume" in
    "$sibling_private_root"|"$sibling_private_root"/*)
      echo "private volume must not live inside a sibling agent private root" >&2
      exit 1
      ;;
  esac
fi

echo "runtime filesystem isolation checks passed"
