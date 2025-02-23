#!/bin/bash
set -e

protocol=$1
rest_time=35
# x=(20 40)
x=(20 40 60 100 150 200 250 300 350 400 450 500 550 600 650 700 750 800 850 900 950 1000)
lastval=${x[${#x[@]}-1]}

run_experiment() {
    local proto=$1

    # Run the application
    cd automation && ./infras.sh run $proto && cd ..

    # loop through x
    for i in "${x[@]}" ; do
        echo "Running $proto with $i vus"

        k6 run --log-output=stdout \
            --summary-export "cpex/prototype/experiments/results/k6/$proto-$i.json" \
            --vus $i \
            --duration 1m \
            "cpex/prototype/experiments/k6/$proto.js"

        if [ $i -lt $lastval ]; then
            echo "Sleeping for $rest_time seconds"
            sleep $rest_time
        fi
    done

    exp_id="3b"
    if [ "$proto" == "atis" ]; then
        exp_id="3a"
    fi

    # Combine k6 results
    python cpex/prototype/experiments/results/scripts/combine_results.py --type k6

    # Run latency experiment
    python cpex/prototype/experiments/scalability.py --experiment $exp_id
}

protocols=(atis cpex)
if [ -n "$protocol" ]; then
    protocols=($protocol)
fi

for proto in "${protocols[@]}"; do
    run_experiment $proto
done

# Combine results for latency measurements
python cpex/prototype/experiments/results/scripts/combine_results.py --type lat
