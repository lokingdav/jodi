#!/bin/bash
set -e

protocol=$1
rest_time=5

func_restart_application() {
    local proto=$1
    cd automation && ./infras.sh run $proto --pull && cd ..
    echo "Sleeping for 15 seconds to let the application start"
    sleep 15
}

func_measure_real_latency() {
    local proto=$1
    exp_id="3b"

    if [ "$proto" == "oobss" ]; then
        exp_id="3a"
    fi

    python jodi/prototype/experiments/scalability.py --experiment $exp_id
}

func_run_latency_experiments() {
    # local x=(20)
    local x=(100 200 400 600 800 1000 1200 1400 1600 1800 2000 2200 2400 2600 2800 3000 3200 3400 3600 3800 4000)
    local lastval=${x[${#x[@]}-1]}
    local proto=$1

    func_restart_application $proto

    for vus in "${x[@]}" ; do
        echo "Running $proto with $vus vus"

        k6 run --log-output=none \
            --env VUS=$vus \
            --summary-export "jodi/prototype/experiments/results/k6/rt_$proto-$vus.json" \
            --vus $vus \
            --duration 1m \
            "jodi/prototype/experiments/k6/$proto.js"

        if [ $vus -lt $lastval ]; then
            echo "Sleeping for $rest_time seconds"
            sleep $rest_time
        fi
    done

    func_measure_real_latency $proto
}

func_run_success_rate_experiments() {
    # local x=(100)
    local x=(100 200 300 400 500 700 900 1000 1500 2000 2500 3000 3500 4000 4500 5000 5500 6000 6500 7000)
    local lastval=${x[${#x[@]}-1]}
    local proto=$1

    func_restart_application $proto

    for vus in "${x[@]}" ; do
        echo "Running $proto with $vus vus"

        k6 run --log-output=none \
            --env VUS=$vus \
            --env TIMEOUT=3s \
            --summary-export "jodi/prototype/experiments/results/k6/sr_$proto-$vus.json" \
            --vus $vus \
            --duration 1m \
            "jodi/prototype/experiments/k6/$proto.js"

        if [ $vus -lt $lastval ]; then
            echo "Sleeping for $rest_time seconds"
            sleep $rest_time
        fi
    done
}

rm jodi/prototype/experiments/results/k6/*.json || true

protocols=(oobss jodi)
if [ -n "$protocol" ]; then
    protocols=($protocol)
fi

for proto in "${protocols[@]}"; do
    func_run_latency_experiments $proto
    func_run_success_rate_experiments $proto
done

# Combine results from multiple files
python jodi/prototype/experiments/results/scripts/combine_results.py --type all
