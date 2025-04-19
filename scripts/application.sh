#!/usr/bin/env bash

CPEX_DOCKER_IMAGE="kofidahmed/cpex"
EXPERIMENTS_IMAGE_NAME="cpex-experiment"
DIND_VM_IMAGE="dindvm"

CPEX_NODE_PREFIX="cpex-node"
CPS_PREFIX="atis-cps"

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
      docker build -f deployments/Dockerfile -t "$EXPERIMENTS_IMAGE_NAME" .
      ;;
    dindvm)
      echo "Building Image for Docker DIND VM"
      docker build -f deployments/Dockerfile.VM -t "$DIND_VM_IMAGE" ./deployments
      ;;
    *)
      echo "Building All Images"
      # docker build -f Dockerfile -t "$CPEX_DOCKER_IMAGE" .
      docker build -f deployments/Dockerfile -t "$EXPERIMENTS_IMAGE_NAME" .
      docker build -f deployments/Dockerfile.VM -t "$DIND_VM_IMAGE" ./deployments
      ;;
  esac

  if [[ "$push" == "--push" ]]; then
    push_image
  fi
}

compose_up() {
  local profile="$1"
  echo "Starting Docker Compose services..."

  rm -rf logs/*.log

  case "$profile" in
    cpex)
      docker compose --profile cpex --profile jodi_proxy --profile experiment up -d
      ;;
    atis)
      docker compose --profile atis --profile oobss_proxy --profile experiment up -d
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
  docker compose --profile cpex --profile jodi_proxy --profile atis --profile experiment --profile db --profile oobss_proxy down --remove-orphans
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
  manage_prod_app ev down
  manage_prod_app ms down
  manage_prod_app cps down
  manage_prod_app cr down
}

initial_setup() {
  echo "Setting up initial configuration..."
  docker exec -it cpex-exp python cpex/prototype/scripts/setup.py --all
}