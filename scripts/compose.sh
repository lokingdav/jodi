#!/bin/bash

# Check for required arguments
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <num_instances> <start_port> <mode>"
    exit 1
fi

# Assign arguments to variables
NUM_INSTANCES=$1
START_PORT=$2
MODE=$3
NETWORK="oobnet"

# Generate the docker-compose.yml file
COMPOSE_FILE="compose.yml"

rm -f $COMPOSE_FILE

cp docker/compose.base.yml $COMPOSE_FILE

echo "" >> $COMPOSE_FILE

for (( i=1; i<=NUM_INSTANCES; i++ ))
do
    NAME="sti-cps-$i"
    HOST_PORT=$((START_PORT + i - 1))

    echo "  $NAME:" >> $COMPOSE_FILE
    echo "    image: oobshaken" >> $COMPOSE_FILE
    echo "    container_name: $NAME" >> $COMPOSE_FILE
    echo "    environment:" >> $COMPOSE_FILE
    echo "      - CPS_SERVICE_ID=$i" >> $COMPOSE_FILE
    echo "      - CPS_NODES_COUNT=$NUM_INSTANCES" >> $COMPOSE_FILE
    echo "      - CPS_OP_MODE=$MODE" >> $COMPOSE_FILE
    echo "    ports:" >> $COMPOSE_FILE
    echo "      - \"$HOST_PORT:80\"" >> $COMPOSE_FILE
    echo "    networks:" >> $COMPOSE_FILE
    echo "      - $NETWORK" >> $COMPOSE_FILE
    echo "    volumes:" >> $COMPOSE_FILE
    echo "      - .:/app" >> $COMPOSE_FILE
    echo "    command: uvicorn server-cps:app --host 0.0.0.0 --port 80 --reload" >> $COMPOSE_FILE
    echo "    depends_on:" >> $COMPOSE_FILE
    echo "      - oob_db" >> $COMPOSE_FILE
    echo "      - sti-ca" >> $COMPOSE_FILE
    echo "" >> $COMPOSE_FILE
done

echo "Generated docker-compose.yml with $NUM_INSTANCES instances, starting from port $START_PORT."

