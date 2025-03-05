#!/bin/bash
set -e

protocol=$1
rest_time=5
x=(20)
# x=(20 40 60 100 150 200 250 300 350 400 450 500 550 600 650 700 750 800 850 900 950 1000)
lastval=${x[${#x[@]}-1]}

restart_application() {
    local proto=$1
    cd automation && ./infras.sh run $proto --pull && cd ..
    echo "Sleeping for 15 seconds to let the application start"
    sleep 15
}

measure_latency() {
    local proto=$1
    exp_id="3b"

    if [ "$proto" == "atis" ]; then
        exp_id="3a"
    fi

    python cpex/prototype/experiments/scalability.py --experiment $exp_id
}

run_experiment() {
    local proto=$1

    restart_application $proto

    for vus in "${x[@]}" ; do
        echo "Running $proto with $vus vus"

        k6 run --log-output=stdout \
            --env VUS=$vus \
            --summary-export "cpex/prototype/experiments/results/k6/$proto-$vus.json" \
            --vus $vus \
            --duration 1m \
            "cpex/prototype/experiments/k6/$proto.js"

        if [ $vus -lt $lastval ]; then
            echo "Sleeping for $rest_time seconds"
            sleep $rest_time
        fi
    done

    measure_latency $proto
}

rm cpex/prototype/experiments/results/k6/*.json || true

protocols=(atis cpex)
if [ -n "$protocol" ]; then
    protocols=($protocol)
fi

for proto in "${protocols[@]}"; do
    run_experiment $proto
done

# Combine results from multiple files
python cpex/prototype/experiments/results/scripts/combine_results.py --type k6
python cpex/prototype/experiments/results/scripts/combine_results.py --type lat
