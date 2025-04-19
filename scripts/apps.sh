#!/usr/bin/env bash

run_control() {
  case "$1" in
    up)
      docker compose --profile control up -d
      ;;
    down)
      docker compose --profile control down
      ;;
    *)
      docker exec -it control bash
      ;;
  esac
}

case "$1" in
  cpex)
    docker compose --profile cpex up -d
    ;;
  atis)
    docker compose --profile atis up -d
    ;;
  control)
    run_control "$2"
    ;;
  down)
    docker compose --profile cpex --profile atis --profile control down
    ;;
  k6)
    runk6 $SUBCMD
    ;;
  *)
    echo "Unknown command: $CMD"
    echo "Available commands: cpex|atis|control|down|k6"
    exit 1
    ;;
esac
