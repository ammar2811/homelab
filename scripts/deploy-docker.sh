#!/usr/bin/env bash
# Sync docker/ from this repo to VM 130 and apply it.
# Usage: scripts/deploy-docker.sh            (sync + docker compose up -d)
#        scripts/deploy-docker.sh --dry-run  (show what would change)
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
host="docker"          # ~/.ssh/config alias for root@10.77.0.30
remote_dir="/opt/homelab"

if [[ "${1:-}" == "--dry-run" ]]; then
  rsync -ain --delete --exclude '*.bak-*' --exclude 'homepage/logs/' "$repo_root/docker/" "$host:$remote_dir/"
  exit 0
fi

rsync -ai --delete --exclude '*.bak-*' --exclude 'homepage/logs/' "$repo_root/docker/" "$host:$remote_dir/"
ssh -o BatchMode=yes "$host" "cd $remote_dir && docker compose config --quiet && docker compose pull --quiet && docker compose up -d --remove-orphans && docker compose ps"
