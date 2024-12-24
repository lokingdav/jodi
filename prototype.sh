#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables from .env file if it exists
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

PROTOCOL_SUITE=${PROTOCOL_SUITE:-cpex}
COMPOSE_FILE=compose.prototype.yml

CMD=$1
VALID_CMDS=('build' 'up' 'down' 'restart' 'ps' 'bash')
MESSAGE_STORE_PREFIX="cpex-ms"
CPS_PREFIX="atis-cps"

# Create configuration directory if it doesn't exist
mkdir -p conf

validate_cmds() {
    if [[ -z "$CMD" ]]; then
        echo "Please provide a command to run: ${VALID_CMDS[*]}"
        exit 1
    fi

    for valid_cmd in "${VALID_CMDS[@]}"; do
        if [[ "$CMD" == "$valid_cmd" ]]; then
            return 0
        fi
    done

    echo "Error: Invalid command '$CMD'. Valid commands are: ${VALID_CMDS[*]}"
    exit 1
}

build_image() {
    echo "Building Docker image '$CPEX_DOCKER_IMAGE'..."
    docker build -f Dockerfile -t "$CPEX_DOCKER_IMAGE" .
}

compose_up() {
    echo "Starting Docker Compose services..."
    docker compose -f $COMPOSE_FILE up -d
    docker exec -it cpex-exp python cpex/prototype/scripts/setup.py --all
}

compose_down() {
    docker ps -aq --filter "name=^${MESSAGE_STORE_PREFIX}" --filter "name=^${CPS_PREFIX}" | grep -q . && \
    echo "Removing Dynamically Added Containers..." && \
    docker ps -aq --filter "name=^${MESSAGE_STORE_PREFIX}" --filter "name=^${CPS_PREFIX}" | xargs docker rm -f

    echo "Stopping Docker Compose services..."
    docker compose -f $COMPOSE_FILE down
}

dockerps() {
    docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
}

open_bash() {
    docker exec -it cpex-exp /bin/bash
}

validate_cmds

case "$CMD" in
    build)
        build_image
        ;;
    up)
        compose_up
        ;;
    down)
        compose_down
        ;;
    restart)
        compose_down
        compose_up
        ;;
    ps)
        dockerps
        ;;
    bash)
        open_bash
        ;;
    *)
        echo "Unknown command: $CMD"
        exit 1
        ;;
esac
