#!/usr/bin/env bash
# Deploy homeassistant/ from this repo to Home Assistant (VM 121) via the Terminal & SSH app.
# Copies configuration.yaml and packages/ (packages/ is mirrored: files removed from the repo
# are removed on HA), runs HA's config check, and restarts HA Core only if the check passes.
# Usage: scripts/deploy-homeassistant.sh            (deploy + check + restart)
#        scripts/deploy-homeassistant.sh --check    (deploy + check, no restart)
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$repo_root/homeassistant"
host="homeassistant"   # ~/.ssh/config alias for root@10.77.0.21 (Terminal & SSH app)
restart=1
[[ "${1:-}" == "--check" ]] && restart=0

stamp="$(date +%Y%m%d-%H%M%S)"
ssh -o BatchMode=yes "$host" "cd /homeassistant && cp -p configuration.yaml configuration.yaml.bak-$stamp \
  && rm -rf packages.new && mkdir -p packages.new"
tar -C "$src" -cf - configuration.yaml packages | ssh -o BatchMode=yes "$host" \
  "cd /homeassistant && tar -xf - --no-same-owner -C packages.new \
   && mv packages.new/configuration.yaml configuration.yaml \
   && rm -rf packages.old && { [ -d packages ] && mv packages packages.old || true; } \
   && mv packages.new/packages packages && rm -rf packages.new packages.old"

echo "== ha core check"
if ! ssh -o BatchMode=yes "$host" "ha core check"; then
  echo "Config check FAILED; restoring previous configuration.yaml (packages left for inspection)." >&2
  ssh -o BatchMode=yes "$host" "cd /homeassistant && cp -p configuration.yaml.bak-$stamp configuration.yaml"
  exit 1
fi

# Keep only the 5 newest configuration.yaml backups.
ssh -o BatchMode=yes "$host" "cd /homeassistant && ls -1t configuration.yaml.bak-* 2>/dev/null | tail -n +6 | xargs -r rm -f"

if (( restart )); then
  echo "== ha core restart"
  ssh -o BatchMode=yes "$host" "ha core restart"
fi
