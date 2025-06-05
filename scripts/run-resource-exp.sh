#!/usr/bin/env bash

node=$1
VUS=1000

k6 run --log-output=none \
    --summary-export "jodi/prototype/experiments/results/resource-exp/$node-$VUS.json" \
    --vus $VUS \
    --duration 10m \
    "jodi/prototype/experiments/k6/$node.js"