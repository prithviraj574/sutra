#!/bin/bash

runtime_root_dir() {
  local script_dir="$1"
  cd "$script_dir/../.." && pwd
}

load_env_file() {
  local env_file="$1"
  local line
  local key
  local value

  while IFS= read -r line || [ -n "$line" ]; do
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
