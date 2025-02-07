#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Load environment variables from .env file if it exists
if [[ -f .env ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs)
fi

###############################################################################
# Configuration Variables
###############################################################################
COMPOSE_FILE="compose.prototype.yml"

CMD="$1"
SUBCMD="$2"

VALID_CMDS=(build up down restart ps bash runexp cpex atis)

# Docker images (adjust names as needed)
CPEX_DOCKER_IMAGE="cpex"
CPEX_AUTOMATION_DOCKER_IMAGE="cpex-automation"

# Optional container naming conventions
CPEX_NODE_PREFIX="cpex-node"
CPS_PREFIX="atis-cps"

# Create configuration directory if it doesn't exist
mkdir -p conf

###############################################################################
# Helper Functions
###############################################################################
validate_cmds() {
  if [[ -z "$CMD" ]]; then
    echo "No command provided. Valid commands are: ${VALID_CMDS[*]}"
    exit 1
  fi

  for valid_cmd in "${VALID_CMDS[@]}"; do
    if [[ "$CMD" == "$valid_cmd" ]]; then
      return 0
    fi
  done

  echo "Error: Invalid command '$CMD'."
  echo "Valid commands are: ${VALID_CMDS[*]}"
  exit 1
}

build_image() {
  local image="$1"

  case "$image" in
    cpex)
      echo "Building CPEX Image"
      docker build -f Dockerfile -t "$CPEX_DOCKER_IMAGE" .
      ;;
    automation)
      echo "Building Image for Automation"
      docker build -f automation/Dockerfile -t "$CPEX_AUTOMATION_DOCKER_IMAGE" .
      ;;
    *)
      echo "Building both Images"
      docker build -f Dockerfile -t "$CPEX_DOCKER_IMAGE" .
      docker build -f automation/Dockerfile -t "$CPEX_AUTOMATION_DOCKER_IMAGE" .
      ;;
  esac
}

compose_up() {
  local profile="$1"
  echo "Starting Docker Compose services..."

  case "$profile" in
    all)
      docker compose -f "$COMPOSE_FILE" up -d
      ;;
    *)
      docker compose -f "$COMPOSE_FILE" up -d experiment automation
      ;;
  esac

  docker exec -it cpex-exp python cpex/prototype/scripts/setup.py --all
}

compose_down() {
  echo "Stopping and removing any dynamically added containers..."
  # Removes containers that match our naming prefixes
  if docker ps -aq --filter "name=^${CPEX_NODE_PREFIX}" --filter "name=^${CPS_PREFIX}" | grep -q .; then
    docker ps -aq --filter "name=^${CPEX_NODE_PREFIX}" --filter "name=^${CPS_PREFIX}" | xargs docker rm -f
  fi

  echo "Stopping Docker Compose services..."
  docker compose -f "$COMPOSE_FILE" down
}

dockerps() {
  docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
}

open_bash() {
  local container="$1"
  # Default container if none specified
  [[ -z "$container" ]] && container="exp"
  local container_name="cpex-$container"

  echo "Opening bash in container: $container_name"
  docker exec -it "$container_name" /bin/bash
}

run_experiments() {
  local exp="$1"
  local allowed=(1 2 3)

  echo "Running experiment '$exp'..."

  # We'll store the base command in an array for safer invocation
  local cmd_base=(docker exec cpex-exp python cpex/prototype/experiments)

  case "$exp" in
    1)
      rm output.log
      "${cmd_base[@]}"/scalability.py --experiment 1 &> output.log
      ;;
    2)
      "${cmd_base[@]}"/microbench.py
      ;;
    3)
      "${cmd_base[@]}"/scalability.py --experiment 3
      ;;
    *)
      echo "Invalid experiment number '$exp'. Allowed values: ${allowed[*]}"
      exit 1
      ;;
  esac
}

manage_prod_app() {
  local app="$1"
  local action="$2"
  local allowed=(up down restart)

  comp_file="compose.$app.yml"

  echo "Running '$app' app with action '$action'..."

  case "$action" in
    up)
      docker compose -f "$comp_file" up -d
      ;;
    down)
      docker compose -f "$comp_file" down
      ;;
    restart)
      docker compose -f "$comp_file" restart
      ;;
    *)
      echo "Invalid action '$action'. Allowed values: ${allowed[*]}"
      exit 1
      ;;
  esac
}

compose_down_all_apps() {
  compose_down
  manage_prod_app cpex down
  manage_prod_app atis down
}

###############################################################################
# Main Script
###############################################################################
validate_cmds

case "$CMD" in
  build)
    build_image "$SUBCMD"
    ;;
  up)
    compose_up "$SUBCMD"
    ;;
  down)
    compose_down_all_apps
    ;;
  restart)
    compose_down_all_apps
    compose_up
    ;;
  ps)
    dockerps
    ;;
  bash)
    open_bash "$SUBCMD"
    ;;
  runexp)
    run_experiments "$SUBCMD"
    ;;
  cpex)
    manage_prod_app cpex "$SUBCMD"
    ;;
  atis)
    manage_prod_app atis "$SUBCMD"
    ;;
  *)
    echo "Unknown command: $CMD"
    exit 1
    ;;
esac
