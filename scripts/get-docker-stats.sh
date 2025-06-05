#!/bin/bash

INTERVAL=10
OUTFILE="jodi/prototype/experiments/results/resource-exp/docker_stats.csv"
INCLUDE_CONTAINERS="evaluator message-store jodi-cache auditlog keyrotation scheduler als_client_worker als_server_worker"  # space-separated

FIELDS="Timestamp,Name,CPUPerc,MemUsage,MemPerc,NetIO,BlockIO,PIDs"

if [ ! -f "$OUTFILE" ]; then
    echo "$FIELDS" > "$OUTFILE"
fi

counter=1
while true; do
    echo "Collecting Docker stats... ${counter}"
    counter=$((counter + 1))

    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}" \
    | grep -E "^($(echo $INCLUDE_CONTAINERS | sed 's/ /|/g'))," \
    | while IFS= read -r line; do
        NAME=$(echo "$line" | cut -d',' -f1)
        CPU=$(echo "$line" | cut -d',' -f2 | tr -d '%')
        MEMUSAGE=$(echo "$line" | cut -d',' -f3 | cut -d'/' -f1 | xargs)
        MEMPER=$(echo "$line" | cut -d',' -f4 | tr -d '%')
        NETIO=$(echo "$line" | cut -d',' -f5 | cut -d'/' -f1 | xargs)
        BLOCKIO=$(echo "$line" | cut -d',' -f6 | cut -d'/' -f1 | xargs)
        PIDS=$(echo "$line" | cut -d',' -f7)
        echo "$(date +%Y-%m-%dT%H:%M:%S),$NAME,$CPU,$MEMUSAGE,$MEMPER,$NETIO,$BLOCKIO,$PIDS" >> "$OUTFILE"
    done
    sleep $INTERVAL
done
