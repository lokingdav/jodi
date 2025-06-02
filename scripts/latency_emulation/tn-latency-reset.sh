#!/usr/bin/env bash
# tn-latency-reset.sh — remove all tc qdiscs
# Usage: sudo ./tn-latency-reset.sh tn-latency.json
# Requires: jq, docker CLI

set -euo pipefail
CONFIG=${1:?Provide JSON topology file}

# Walk through every container/if tuple in the JSON and delete its root qdisc
jq -r '.containers | to_entries[] | "\(.key) \(.value.if)"' "$CONFIG" |
while read -r cname ifname; do
  echo "↻  resetting $cname ($ifname)"
  docker exec -u root "$cname" tc qdisc del dev "$ifname" root 2>/dev/null || true
done

echo "✅  all qdiscs removed"
