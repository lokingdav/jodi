#!/bin/bash
set -e

protocol=$1

if [ -z "$protocol" ]; then
    echo "Usage: $0 <protocol>"
    exit 1
fi

rest_time=35
x=(20 40 60 100 150 200 250 300 350 400 450 500 550 600 650 700 750 800 850 900 950 1000)
lastval=${x[${#x[@]}-1]}

# loop through x
for i in "${x[@]}" ; do
    echo "Running $protocol with $i vus"

    k6 run --log-output=stdout \
        --summary-export "cpex/prototype/experiments/results/k6/$protocol-$i.json" \
        --vus $i \
        --duration 1m \
        "cpex/prototype/experiments/k6/$protocol.js"

    # if $i < $lastval sleep
    if [ $i -lt $lastval ]; then
        echo "Sleeping for $rest_time seconds"
        sleep $rest_time
    fi
done