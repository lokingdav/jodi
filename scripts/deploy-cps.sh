#!/bin/bash

# Configuration
instances=${1:-5}        # Number of instances to run
image=${3}     # Specify the Docker image to use
start_port="$2:-5000"        # Starting port number

# Build the Docker image from Dockerfile
docker build --no-cache -t $image -f Dockerfile .

# Loop to create and run each instance
for i in $(seq 1 $instances); do
    # Calculate the port number for this instance
    port=$(($start_port + $i - 1))
    
    # Run the Docker container
    docker run -d \
        --name "$image-$i" \
        -p "$port:5000" \
        -e NODE_NAME="$image-$i" \
        -e NODE_ENV="development" \
        $image
    
    echo "Started node$i on port $port"
done

echo "All nodes are up and running."
