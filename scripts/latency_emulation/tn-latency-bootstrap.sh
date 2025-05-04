#!/usr/bin/env bash
# -------------------------------------------------------------------
#  tn-latency-bootstrap.sh
#  Installs ping + tc (iputils-ping, iproute2) in every container
#
#  USAGE: sudo ./tn-latency-bootstrap.sh tn-latency.json
# -------------------------------------------------------------------

set -euo pipefail
CONFIG=${1:?Provide JSON topology file}

# Grab the container list from .containers{...}
jq -r '.containers | keys[]' "$CONFIG" | while read -r cname; do
  echo "🛠  Setting up $cname …"

  # Try the Debian/Ubuntu path first
  if docker exec -u root "$cname" sh -c \
      'command -v apt-get >/dev/null 2>&1'; then
    echo "   → using apt-get"
    if docker exec -u root "$cname" sh -c \
         'apt-get update -qq && \
          DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iproute2 iputils-ping'; then
      echo "   ✓ installed via apt"
      continue
    else
      echo "   ⚠️  apt path failed, falling back to apk"
    fi
  fi

  # Alpine / apk path
  if docker exec -u root "$cname" sh -c \
      'command -v apk >/dev/null 2>&1'; then
    docker exec -u root "$cname" sh -c \
      'apk update -q && apk add --no-cache iproute2 iputils'
    echo "   ✓ installed via apk"
  else
    echo "   ❌ neither apt-get nor apk found in $cname — skipped" >&2
  fi
done

echo "✅  All containers processed"