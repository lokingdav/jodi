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
CMD="$1"
SUBCMD="$2"

VALID_CMDS=(build push-img up down restart ps bash runexp cpex atis k6)

# Docker images (adjust names as needed)
CPEX_DOCKER_IMAGE="kofidahmed/cpex"
CPEX_AUTOMATION_DOCKER_IMAGE="cpex-experiment"

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

push_image() {
  echo "Pushing $CPEX_DOCKER_IMAGE to Docker Hub..."
  docker push "$CPEX_DOCKER_IMAGE"
}

build_image() {
  local image="$1"
  local push="$2"

  case "$image" in
    cpex)
      echo "Building CPEX Image"
      docker build -f Dockerfile -t "$CPEX_DOCKER_IMAGE" .
      ;;
    experiment)
      echo "Building Image for Experimentation"
      docker build -f automation/Dockerfile -t "$CPEX_AUTOMATION_DOCKER_IMAGE" .
      ;;
    *)
      echo "Building both Images"
      docker build -f Dockerfile -t "$CPEX_DOCKER_IMAGE" .
      docker build -f automation/Dockerfile -t "$CPEX_AUTOMATION_DOCKER_IMAGE" .
      ;;
  esac

  if [[ "$push" == "--push" ]]; then
    push_image
  fi
}

initial_setup() {
  echo "Setting up initial configuration..."
  docker exec -it cpex-exp python cpex/prototype/scripts/setup.py --all
}

compose_up() {
  local profile="$1"
  echo "Starting Docker Compose services..."

  case "$profile" in
    cpex)
      docker compose --profile cpex --profile proxy --profile experiment up -d
      ;;
    atis)
      docker compose --profile atis --profile experiment up -d
      ;;
    all)
      docker compose --profile cpex --profile atis --profile experiment up -d
      ;;
    *)
      docker compose --profile experiment up -d
      ;;
  esac

  initial_setup
}

compose_down() {
  echo "Stopping and removing any dynamically added containers..."
  # Removes containers that match our naming prefixes
  if docker ps -aq --filter "name=^${CPEX_NODE_PREFIX}" --filter "name=^${CPS_PREFIX}" | grep -q .; then
    docker ps -aq --filter "name=^${CPEX_NODE_PREFIX}" --filter "name=^${CPS_PREFIX}" | xargs docker rm -f
  fi

  echo "Stopping Docker Compose services..."
  docker compose --profile cpex --profile proxy --profile atis --profile experiment --profile db down --remove-orphans
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

  echo "Running '$app' app with action '$action'..."

  case "$action" in
    up)
      docker compose --profile "$app" up -d
      ;;
    down)
      docker compose --profile "$app" down
      ;;
    restart)
      docker compose --profile "$app" restart
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

runk6() {
  local name="$1"
  local allowed=(ev ms cpex atis)
  local config="options.json"
  local summary=""
  local test_file=""
  
  case "$name" in
    ev)
      summary="k6-ev.json"
      test_file="ev.js"
      ;;
    ms)
      summary="k6-ms.json"
      test_file="ms.js"
      ;;
    p)
      summary="k6-p.json"
      test_file="p.js"
      ;;
    cpex)
      config="prod.json"
      summary="k6-cpex.json"
      test_file="cpex.js"
      ;;
    atis)
      config="prod.json"
      summary="k6-atis.json"
      test_file="atis.js"
      ;;
    *)
      echo "Invalid experiment name '$name'. Allowed values: ${allowed[*]}"
      exit 1
      ;;
  esac

  k6 run --log-output=stdout \
    --config "cpex/prototype/experiments/k6/$config" \
    --summary-export "$summary" cpex/prototype/experiments/k6/$test_file
}

###############################################################################
# Main Script
###############################################################################
validate_cmds

case "$CMD" in
  build)
    build_image "$SUBCMD" "$3"
    ;;
  push-img)
    push_image
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
  k6)
    runk6 $SUBCMD
    ;;
  *)
    echo "Unknown command: $CMD"
    exit 1
    ;;
esac
