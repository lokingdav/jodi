#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables from .env file if it exists
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

COMPOSE_FILE=compose.prototype.yml

CMD=$1
VALID_CMDS=('build' 'up' 'down' 'restart' 'ps' 'bash' 'runexp')
CPEX_NODE_PREFIX="cpex-node"
CPS_PREFIX="atis-cps"
CPEX_DOCKER_IMAGE="cpex"

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
    local service=$1
    echo "Starting Docker Compose services..."
    if [[ -z "$service" ]]; then
        docker compose -f $COMPOSE_FILE up -d
        docker exec -it cpex-exp python cpex/prototype/scripts/setup.py --all
    else
        docker compose -f $COMPOSE_FILE up -d "$service"
    fi
}

compose_down() {
    docker ps -aq --filter "name=^${CPEX_NODE_PREFIX}" --filter "name=^${CPS_PREFIX}" | grep -q . && \
    echo "Removing Dynamically Added Containers..." && \
    docker ps -aq --filter "name=^${CPEX_NODE_PREFIX}" --filter "name=^${CPS_PREFIX}" | xargs docker rm -f

    echo "Stopping Docker Compose services..."
    docker compose -f $COMPOSE_FILE down
}

dockerps() {
    docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
}

open_bash() {
    local container_name=$1
    [[ -z "$container_name" ]] && container_name="exp"
    container_name="cpex-$container_name"
    docker exec -it $container_name /bin/bash
}

run_experiments() {
    local exp=$1
    local allowed=(1 2)

    echo "Running experiment '$exp'..."
    cmd_prefix="docker exec -it cpex-exp python cpex/prototype/experiments"

    case "$exp" in
        1)
            $cmd_prefix"/microbench.py"
            ;;
        2)
            $cmd_prefix"/scalability.py"
            ;;
        *)
            echo "Invalid experiment number. Allowed: ${allowed[*]}"
            exit 1
            ;;
    esac
    
}

validate_cmds

case "$CMD" in
    build)
        build_image
        ;;
    up)
        compose_up $2
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
        open_bash $2
        ;;
    runexp)
        run_experiments $2
        ;;
    *)
        echo "Unknown command: $CMD"
        exit 1
        ;;
esac
