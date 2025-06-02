#!/usr/bin/env bash
# -------------------------------------------------------------------
#  Configure inter‑AZ latency inside running Docker containers
#  Requires: bash ≥4, jq, tc in each container, docker CLI on host
#
#  USAGE:  sudo ./tn-latency-set.sh tn-latency.json
# -------------------------------------------------------------------
set -euo pipefail
CONFIG=${1:?Provide JSON config path}

jq_get() { jq -r "$1" "$CONFIG"; }

# ---------- read topology ---------------------------------------------------
mapfile -t ZONES < <(jq_get '.zones | keys[]')

declare -A Z_CONT Z_OF IP IFACE          # zone→containers  /  container→zone/ip/if

for z in "${ZONES[@]}"; do
  mapfile -t arr < <(jq_get ".zones[\"$z\"][]")
  Z_CONT[$z]="${arr[*]}"
  for c in ${arr[*]}; do
    IP[$c]=$(jq_get ".containers[\"$c\"].ip")
    IFACE[$c]=$(jq_get ".containers[\"$c\"].if")
    Z_OF[$c]=$z
  done
done

# ---------- build delay lookup from .links[] and intra_zone_latency_ms ------
declare -A DELAY   # key="src|dst" → ms

INTRA_MS=$(jq -r '.intra_zone_latency_ms // empty' "$CONFIG")
[[ -z $INTRA_MS ]] && INTRA_MS=0 

while IFS= read -r link; do
  src=$(jq -r '.zones[0]' <<<"$link")
  dst=$(jq -r '.zones[1]' <<<"$link")
  ms=$( jq -r '.latency_ms'  <<<"$link")
  DELAY["$src|$dst"]=$ms     # A → B
  DELAY["$dst|$src"]=$ms     # B → A (symmetry)
done < <(jq -c '.links[]' "$CONFIG")

if (( INTRA_MS > 0 )); then
  for z in $(jq -r '.zones | keys[]' "$CONFIG"); do
    DELAY["$z|$z"]=$INTRA_MS
  done
fi

# ---------- helper funcs ----------------------------------------------------
ensure_htb_root() {  # $1 container  $2 if
  docker exec -u root $1 tc qdisc del dev $2 root 2>/dev/null || true
  docker exec -u root $1 tc qdisc add dev $2 root handle 1: htb default 999 r2q 10000
  docker exec -u root $1 tc class add dev $2 parent 1: classid 1:999 htb rate 1000mbit
}
add_latency_class() { # $1 cont $2 if $3 clsid $4 delay
  docker exec -u root $1 tc class add dev $2 parent 1: classid 1:$3 htb rate 1000mbit
  docker exec -u root $1 tc qdisc add  dev $2 parent 1:$3 handle $3: netem delay ${4}ms
}
add_ip_filter() {     # $1 cont $2 if $3 dstIP $4 clsid
  docker exec -u root $1 tc filter add dev $2 protocol ip parent 1: prio 1 u32 \
       match ip dst $3/32 flowid 1:$4
}

# ---------- apply tc --------------------------------------------------------
for c in "${!IP[@]}"; do
  s_zone=${Z_OF[$c]}
  ifname=${IFACE[$c]}

  echo "⎈ configuring $c ($s_zone) on $ifname"
  ensure_htb_root "$c" "$ifname"

  declare -A CLS_FOR_DELAY=()
  next_cls=10

  for d_zone in "${ZONES[@]}"; do
    d_ms=${DELAY["$s_zone|$d_zone"]-}
    [[ -z $d_ms ]] && continue     # skip if no entry

    cls=${CLS_FOR_DELAY[$d_ms]-}
    if [[ -z $cls ]]; then
      cls=$next_cls; CLS_FOR_DELAY[$d_ms]=$cls
      add_latency_class "$c" "$ifname" "$cls" $(((d_ms + 1) / 2))
      ((next_cls++))
    fi

    for tgt in ${Z_CONT[$d_zone]}; do
      add_ip_filter "$c" "$ifname" "${IP[$tgt]}" "$cls"
    done
  done
done

echo "✅ latency profile applied"

# Run this script only when the containers are running