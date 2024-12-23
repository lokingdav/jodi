#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables from .env file if it exists
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

LOCK_FILE="services.lock"

# Define variables with defaults if not set
PROTOCOL_SUITE=${PROTOCOL_SUITE:-cpex}
CPEX_DOCKER_IMAGE=${CPEX_DOCKER_IMAGE:-cpex}
COMPOSE_NETWORK_ID=${COMPOSE_NETWORK_ID:-cpex_net}

REPOSITORIES_COUNT=${REPOSITORIES_COUNT:-10}
STARTING_REPOSITORY_PORT=${STARTING_REPOSITORY_PORT:-10000}

display_configuration() {
    echo "Control Plane Extension Prototype Configuration"
    echo "-> Protocol Suite: $PROTOCOL_SUITE"
    echo "-> Docker Image: $CPEX_DOCKER_IMAGE"
    echo "-> Docker Compose Network ID: $COMPOSE_NETWORK_ID"
    echo "-> Base Repository Port: $STARTING_REPOSITORY_PORT"
    echo "-> Repositories Count: $REPOSITORIES_COUNT"
    echo ""
}

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

add_repository_node() {
    local repo_id=$1

    if [[ -z "$repo_id" ]]; then
        echo "Error: Repository ID is required to add a node."
        exit 1
    fi

    local port=$((STARTING_REPOSITORY_PORT + repo_id))
    local name="${MESSAGE_STORE_PREFIX}-${repo_id}"
    local command="uvicorn cpex.servers.message_store:app --host 0.0.0.0 --port 80 --reload"
    local fqdn="$name"
    local nodeId=$(echo -n "$name" | sha1sum | awk '{print $1}')

    # if protocol suite is atis, use atis-cps as the container name
    if [[ "$PROTOCOL_SUITE" == "atis" ]]; then
        name="${CPS_PREFIX}-${repo_id}"
        command="uvicorn cpex.prototype.stirshaken.cps_server:app --host 0.0.0.0 --port 80 --reload"
        fqdn="$name"
    fi

    echo "Adding repository node with ID: $repo_id"
    echo "-> Protocol Suite: $PROTOCOL_SUITE"
    echo "-> Container Name: $name"
    echo "-> Port: $port"
    echo "-> FQDN: $fqdn"

    docker run -d \
        --name "$name" \
        --network "$COMPOSE_NETWORK_ID" \
        -p "0.0.0.0:$port:80/tcp" \
        -e "NODE_ID=$nodeId" \
        -e "REPO_PORT=$port" \
        -e "REPO_FQDN=$fqdn" \
        -v "$(pwd):/app:rw" \
        "$CPEX_DOCKER_IMAGE" \
        $command
    
    # Append $name, $port to conf/repositories.json
    echo "{\"id\": \"$nodeId\", \"name\": \"$name\", \"fqdn\": \"$name\", \"url\": \"http://$fqdn\"}," >> conf/repositories.json
    echo ""
}

compose_up() {
    display_configuration
    
    # Check if lock file exists
    if [[ -f "$LOCK_FILE" ]]; then
        echo "Docker Compose services are already running. Please run 'bin/cpex.sh down' to stop them."
        exit 1
    fi

    echo "Starting Docker Compose services..."
    docker compose up -d

    echo "Adding $REPOSITORIES_COUNT Repository nodes"
    echo "[" > conf/repositories.json
    for (( cps_id=1; cps_id<=REPOSITORIES_COUNT; cps_id++ )); do
        add_repository_node "$cps_id"
    done
    # Remove trailing comma
    sed -i '$ s/.$//' conf/repositories.json
    echo "]" >> conf/repositories.json
    echo "Docker Compose services started successfully!" > $LOCK_FILE
    docker exec -it cpex-exp python cpex/prototype/scripts/setup.py --repos --groupsig
}

compose_down() {
    if [[ ! -f "$LOCK_FILE" ]]; then
        echo "Docker Compose services are not running. Please run 'bin/cpex.sh up' to start them."
        exit 1
    fi
    echo "Removing Dynamically Added CPS nodes..."
    docker ps -aq --filter "name=^${MESSAGE_STORE_PREFIX}" --filter "name=^${CPS_PREFIX}" | xargs docker rm -f
    echo "Stopping Docker Compose services..."
    docker compose down
    rm -f $LOCK_FILE
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
