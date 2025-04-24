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
    echo "$0 images {build|push} [main|control|dindvm] [--push]" # e.g ./prototype.sh images build
    echo "$0 infras create {livenet|testnet}" # e.g ./prototype.sh infras create testnet
    echo "$0 infras install" # install dependencies on the infrastructure nodes
    echo "$0 infras run {jodi|oobss}"
    exit 1
    ;;
esac
