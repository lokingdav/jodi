#!/usr/bin/env bash

set -e

CMD="$1"
IMG="$2"

MAIN_IMAGE="kofidahmed/jodi"
CONTROL_IMAGE="jodi-control"
DIND_VM_IMAGE="dindvm"

push_image() {
  echo "Pushing $MAIN_IMAGE to Docker Hub..."
  docker push "$MAIN_IMAGE"
}

build_image() {
  local img="$1"
  local push="$2"

  case "$img" in
    main)
      echo "Building $MAIN_IMAGE"
      docker build -f Dockerfile.jodi -t "$MAIN_IMAGE" .
      ;;
    control)
      echo "Building $CONTROL_IMAGE"
      docker build -f Dockerfile.control -t "$CONTROL_IMAGE" .
      ;;
    dindvm)
      echo "Building $DIND_VM_IMAGE"
      docker build -f Dockerfile.vm -t "$DIND_VM_IMAGE" .
      ;;
    *)
      echo "Building All Images: $MAIN_IMAGE, $CONTROL_IMAGE, $DIND_VM_IMAGE"
      docker build -f Dockerfile.jodi -t "$MAIN_IMAGE" .
      docker build -f Dockerfile.control -t "$CONTROL_IMAGE" .
      docker build -f Dockerfile.vm -t "$DIND_VM_IMAGE" .
      ;;
  esac

  if [[ "$push" == "--push" ]]; then
    push_image
  fi
}

case "$CMD" in
  build)
    build_image "$IMG" "$3"
    ;;
  push)
    push_image
    ;;
  *)
    echo "Unknown command: $CMD"
    echo "Usage: {build|push} [image] [--push]"
    echo "Available images: main, control, dindvm"
    exit 1
    ;;
esac
