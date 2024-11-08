#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables from .env file if it exists
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Define variables with defaults if not set
BASE_CPS_PORT=${BASE_CPS_PORT:-10000}
CPEX_DOCKER_IMAGE=${CPEX_DOCKER_IMAGE:-cpex}
COMPOSE_NETWORK_ID=${COMPOSE_NETWORK_ID:-cpex_net}

CMD=$1
CPS_NODES=$2

VALID_CMDS=('build' 'up' 'down' 'restart' 'ps' 'add-cps' 'bash')
CONTAINER_PREFIX="cpex-cps-"

# Create configuration directory if it doesn't exist
mkdir -p conf

# Function to validate the provided command
validate_cmds() {
    if [[ -z "$CMD" ]]; then
        echo "Please provide a command to run: ${VALID_CMDS[*]}"
        exit 1
    fi

    for valid_cmd in "${VALID_CMDS[@]}"; do
        if [[ "$CMD" == "$valid_cmd" ]]; then
            return 0  # Command is valid
        fi
    done

    echo "Error: Invalid command '$CMD'. Valid commands are: ${VALID_CMDS[*]}"
    exit 1
}

# Function to build the Docker image
build_image() {
    echo "Building Docker image '$CPEX_DOCKER_IMAGE'..."
    docker build -f Dockerfile -t "$CPEX_DOCKER_IMAGE" .
}

# Function to add a single CPS node
add_cps_node() {
    local cps_id=$1

    if [[ -z "$cps_id" ]]; then
        echo "Error: CPS ID is required to add a CPS node."
        exit 1
    fi

    local port=$((BASE_CPS_PORT + cps_id))
    local name="${CONTAINER_PREFIX}${cps_id}"

    echo "Adding CPS node with ID: $cps_id"
    echo "Container Name: $name"
    echo "Port: $port"

    docker run -d \
        --name "$name" \
        --network "$COMPOSE_NETWORK_ID" \
        -p "0.0.0.0:$port:8888/tcp" \
        -e "CPS_ID=$cps_id" \
        -e "CPS_PORT=$port" \
        -v "$(pwd)/:/app:rw" \
        "$CPEX_DOCKER_IMAGE" \
        uvicorn cpex.servers.cps_server:app --host 0.0.0.0 --port 8888 --reload
    echo ""
}

# Function to start Docker Compose services and add initial CPS nodes
compose_up() {
    echo "Starting Docker Compose services..."
    docker compose up -d

    if [[ -z "$CPS_NODES" ]]; then
        echo "CPS_NODES is not provided. Attempting to read from .env..."
        CPS_NODES=$(grep '^INITIAL_CPS_NODES=' .env | cut -d '=' -f2-)
        if [[ -z "$CPS_NODES" ]]; then
            echo "Error: INITIAL_CPS_NODES is not set in .env and CPS_NODES argument is empty."
            exit 1
        fi
    fi

    echo "Adding CPS nodes: $CPS_NODES"
    IFS=',' read -ra NODE_IDS <<< "$CPS_NODES"
    for cps_id in "${NODE_IDS[@]}"; do
        add_cps_node "$cps_id"
    done
}

# Function to stop Docker Compose services and remove CPS nodes
compose_down() {
    echo "Removing Dynamically Added CPS nodes..."
    docker ps -aq --filter "name=^${CONTAINER_PREFIX}" | xargs -r docker rm -f
    echo "Stopping Docker Compose services..."
    docker compose down
}

# Function to list running Docker containers
dockerps() {
    docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# Function to add multiple CPS nodes with automatic ID assignment
add_cps_command() {
    local N=$CPS_NODES

    if [[ -z "$N" ]]; then
        echo "Error: Number of CPS nodes to add is required for 'add-cps' command."
        exit 1
    fi

    # Validate that N is a positive integer
    if ! [[ "$N" =~ ^[0-9]+$ ]]; then
        echo "Error: Number of CPS nodes to add must be a positive integer."
        exit 1
    fi

    # Get S: count of existing containers with names starting with 'cpex-cps-'
    local S=$(docker ps -aq --filter "name=^${CONTAINER_PREFIX}" | wc -l)

    echo "Existing CPS nodes count: $S"
    echo "Adding $N CPS node(s), assigning IDs from $((S)) to $((S + N))"

    for ((i=0; i<N; i++)); do
        local cps_id=$((S + i))
        add_cps_node "$cps_id"
    done
}

open_bash() {
    echo "Welcome! Control Plane Extension System"
    docker exec -it cpex-exp /bin/bash
}

# Validate the provided command
validate_cmds

# Execute the corresponding function based on the command
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
    add-cps)
        add_cps_command
        ;;
    bash)
        open_bash
        ;;
    *)
        echo "Unknown command: $CMD"
        exit 1
        ;;
esac
