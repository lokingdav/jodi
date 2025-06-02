#!/bin/bash
set -e

# Configuration
NETWORK_NAME="jodi_testnet"
DURATION="10m"         # Duration of network emulation (5m, 1h, etc.)
LATENCY="100"          # Base latency to add, in milliseconds (no 'ms')
JITTER="20"            # Jitter in milliseconds (no 'ms')
INTERFACE="eth0"       # Network interface to affect
TC_IMAGE="gaiadocker/iproute2"  # Use a public tc image

# Get all RUNNING containers in the target network
containers=$(docker network inspect $NETWORK_NAME --format '{{range .Containers}}{{.Name}} {{end}}' | xargs -n1 | while read container; do
  if [ "$(docker inspect -f '{{.State.Running}}' $container 2>/dev/null)" == "true" ]; then
    if [ "$container" != "jodi-control" ]; then
      echo "$container"
    fi
  fi
done | xargs)

if [ -z "$containers" ]; then
  echo "No running containers found in network $NETWORK_NAME"
  exit 1
fi

echo "Targeting running containers:"
echo "$containers"

# Execute Pumba netem command
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gaiaadm/pumba:latest \
  netem --tc-image $TC_IMAGE \
  --interface $INTERFACE \
  --duration $DURATION \
  delay --time $LATENCY --jitter $JITTER \
  $containers

echo "Applied ${LATENCY}ms ± ${JITTER}ms latency to all running containers in $NETWORK_NAME for $DURATION"