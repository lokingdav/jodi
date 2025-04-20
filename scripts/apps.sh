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
      docker exec -it jodi-control bash
      ;;
  esac
}

case "$1" in
  jodi)
    docker compose --profile jodi up -d
    ;;
  oobss)
    docker compose --profile oobss up -d
    ;;
  control)
    run_control "$2"
    ;;
  down)
    docker compose --profile jodi --profile oobss --profile control down
    ;;
  k6)
    runk6 $SUBCMD
    ;;
  *)
    echo "Unknown command: $CMD"
    echo "Available commands: jodi|oobss|control|down|k6"
    exit 1
    ;;
esac
