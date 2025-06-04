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
  jodi_all)
    docker compose --profile jodi_cps --profile jodi_als up -d --remove-orphans
    ;;
  jodi_cps)
    docker compose --profile jodi_cps up -d
    ;;
  jodi_als)
    docker compose --profile jodi_als up -d
    ;;
  oobss)
    docker compose --profile oobss up -d
    ;;
  control)
    run_control "$2"
    ;;
  down)
    docker compose --profile jodi_cps --profile jodi_als --profile oobss --profile control down
    ;;
  k6)
    runk6 $SUBCMD
    ;;
  *)
    echo "Unknown command: $CMD"
    echo "Available commands: jodi_cps|jodi_als|oobss|control|down|k6"
    exit 1
    ;;
esac
