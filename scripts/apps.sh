#!/usr/bin/env bash

case "$1" in
  cpex)
    docker compose --profile cpex up -d
    ;;
  atis)
    docker compose --profile atis up -d
    ;;
  control)
    docker compose --profile experiment up -d
    ;;
  down)
    docker compose --profile cpex --profile atis --profile experiment down
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
