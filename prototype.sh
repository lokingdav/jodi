#!/usr/bin/env bash

set -e

mkdir -p conf

case "$1" in
  images)
    ./scripts/images.sh "$2" "$3"
    ;;
  infras)
    ./scripts/infras.sh "$2" "$3"
    ;;
  control)
    ./scripts/apps.sh control $2
    ;;
  *)
    echo "Usage: $0 {images|infras|control} [args...]"
    echo "Commands:"
    echo "$0 images {build|push} [main|experiment|dindvm] [--push]"
    echo "$0 infras create {livenet|testnet}"
    exit 1
    ;;
esac
