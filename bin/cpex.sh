#!/bin/bash
CMD=$1

VALID_CMDS=('build' 'up' 'down')
CONTAINER_PREFIX="cpex_dyn_"

validate_docker_path() {
    # Define default socket path based on the operating system
    if [[ -z "$DOCKER_SOCKET_PATH" ]]; then
        if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
            DOCKER_SOCKET_PATH="/var/run/docker.sock"
        elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
            # Adapt for Windows if needed
            DOCKER_SOCKET_PATH="//var/run/docker.sock"
        else
            echo "Unsupported OS: $OSTYPE. Please set DOCKER_SOCKET_PATH manually."
            exit 1
        fi
    fi
}

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

build_image() {
    docker build -f Dockerfile -t cpex .
}

compose_up() {
    # Check if DOCKER_SOCKET_PATH is set and not empty
    if [[ -z "$DOCKER_SOCKET_PATH" ]]; then
        echo "Error: DOCKER_SOCKET_PATH environment variable is not set. Please set it to the path of the Docker socket (e.g., /var/run/docker.sock)."
        exit 1
    fi

    docker compose up -d

    INITIAL_CPS_NODES=$(grep '^INITIAL_CPS_NODES=' .env | cut -d '=' -f2-)

    docker run \
        -v "$(pwd)":/app \
        -v "$DOCKER_SOCKET_PATH":/var/run/docker.sock \
        -e DOCKER_SOCKET_PATH="$DOCKER_SOCKET_PATH" \
        --rm cpex python /app/initcps.py --initial-cps-nodes "$INITIAL_CPS_NODES"
}

compose_down() {
    docker ps -aq --filter "name=^$CONTAINER_PREFIX" | xargs -r docker rm -f
    docker compose down
}

validate_docker_path
validate_cmds
echo "Executing 'cpex $CMD' command"
if [[ $CMD == 'build' ]]; then
    build_image
elif [[ $CMD == 'up' ]]; then
    compose_up
elif [[ $CMD == 'down' ]]; then
    compose_down
fi
