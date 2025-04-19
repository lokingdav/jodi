#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

###############################################################################
# Configuration Variables
###############################################################################
CMD="$1"
SUBCMD="$2"

VALID_CMDS=(build push-img up down restart ps bash runexp cpex atis ev ms cps cr k6)

# Create configuration directory if it doesn't exist
mkdir -p conf


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
  ev)
    manage_prod_app ev "$SUBCMD"
    ;;
  ms)
    manage_prod_app ms "$SUBCMD"
    ;;
  cps)
    manage_prod_app cps "$SUBCMD"
    ;;
  cr)
    manage_prod_app cr "$SUBCMD"
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
