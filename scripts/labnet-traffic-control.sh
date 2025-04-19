#!/usr/bin/env bash
set -euo pipefail

BR_B=$(docker network inspect -f '{{ .Options.bridge }}' netB 2>/dev/null ||
       docker network inspect -f '{{ index .Id | printf "br-%s" | trunc 12 }}' netB)

case "${1:-start}" in
  start)
    tc qdisc replace dev "$BR_B" root handle 1: netem \
        delay 120ms 15ms distribution normal \
        loss 0.5% rate 10mbit
    ;;
  stop)
    tc qdisc del dev "$BR_B" root || true
    ;;
esac
