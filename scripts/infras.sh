#!/bin/bash

set -e

MAIN_HOSTS_FILE=hosts.yml
TESTNET_COMPOSE_FILE=compose.testnet.yml

# Panic if DOCKER_SOCKET_PATH is not set
if [ -z "$DOCKER_SOCKET_PATH" ]; then
    echo "Error: DOCKER_SOCKET_PATH is not set."
    echo "You can set it by running: export DOCKER_SOCKET_PATH=/var/run/docker.sock"
    echo "Press Ctrl+C to exit. Otherwise it will be set to /var/run/docker.sock in 5 seconds."
    sleep 5
    DOCKER_SOCKET_PATH=/var/run/docker.sock
fi

run_in_docker() {
    local command=$1
    local app_dir=$(pwd)

    docker run -it --rm \
        -v "$app_dir:/app" \
        -v "$app_dir/docker/data/.aws:/root/.aws" \
        -v "$app_dir/docker/data/.ssh:/root/.ssh" \
        -v "$DOCKER_SOCKET_PATH":"$DOCKER_SOCKET_PATH" \
        -e ANSIBLE_HOST_KEY_CHECKING=False \
        -e ANSIBLE_CONFIG=/app/deployments/ansible.cfg \
        jodi-control \
        /bin/bash -c "cd /app && $command"
}

init() {
    run_in_docker "./scripts/livenet-configure.sh"
}

create() {
    local network=$1

    # if main main.yml exists, notify and exit with error
    hosts_file="deployments/$MAIN_HOSTS_FILE"
    if [ -f "$hosts_file" ]; then
        echo "Error: $hosts_file already exists. Please run 'infras destroy' to destroy the current setup before creating a new infrastructure."
        exit 1
    fi

    case "$network" in
        livenet)
            echo "Creating Livenet Cloud Infrastructure..."
            run_in_docker "cd deployments && terraform apply"
            ;;
        testnet)
            echo "Creating Testnet Infrastructure..."
            docker compose -f $TESTNET_COMPOSE_FILE up -d
            run_in_docker "python jodi/prototype/scripts/setup.py --testnet"
            ;;
        *)
            echo "Available subcommands for create:"
            echo "create {livenet|testnet}"
            exit 1
            ;;
    esac

    run_in_docker "python jodi/prototype/scripts/setup.py --loads"
    
    echo "Infrastructure created successfully."
}

destroy() {
    echo "1. Destroying Testnet Infrastructure (if applicable)..."
    docker compose -f $TESTNET_COMPOSE_FILE down
    rm_files="rm -rf $MAIN_HOSTS_FILE"
    echo "2. Destroying Livenet Cloud Infrastructure (if applicable)..."
    run_in_docker "cd deployments && terraform destroy && $rm_files"

    echo "Destroyed all resources successfully."
}

reset() {
    echo "Resetting infrastructure..."
    destroy
    run_in_docker "rm -rf docker/data/testnet"
}

install() {
    pull="$1"
    run_in_docker "cd deployments && ansible-playbook -i $MAIN_HOSTS_FILE playbooks/install.yml $pull"
}

pull_changes() {
    install "--tags 'checkout_branch'"
}

runapp() {
    local app=$1
    local pull=$2
    local directly=$3

    tags="stop_services,clear_logs"
    if [ "$pull" == "--pull" ]; then
        tags="$tags,checkout_branch"
    fi

    case "$app" in
        jodi)
            tags="$tags,start_jodi"
            ;;
        oobss)
            tags="$tags,start_oobss"
            ;;
        *)
            echo "Unknown app: $app"
            echo "Usage: infras run {jodi|oobss}"
            exit 1
            ;;
    esac

    local cmd_str="cd deployments && ansible-playbook -i $MAIN_HOSTS_FILE playbooks/main.yml --tags $tags"
    
    if [ "$directly" == "--directly" ]; then
        eval "$cmd_str"
    else
        run_in_docker "$cmd_str"
    fi
}

latency() {
    local action=$1
    local config_file="./scripts/latency_emulation/tn-latency.json"

    case "$action" in
        set)
            ./scripts/latency_emulation/tn-latency-set.sh $config_file
            ;;
        unset)
            ./scripts/latency_emulation/tn-latency-reset.sh $config_file
            ;;
        *)
            echo "Usage: infras latency {set|unset}"
            exit 1
            ;;
    esac
}

case "$1" in
    init)
        init
        ;;
    create)
        create $2
        ;;
    destroy)
        destroy
        ;;
    reset)
        reset
        ;;
    install)
        install
        ;;
    pull)
        pull_changes
        ;;
    run)
        runapp "$2" "$3" "$4"
        ;;
    latency)
        latency "$2"
        ;;
    *)
        echo "Usage: infras {init|create|destroy|install|pull|run} [args...]"
        exit 1
        ;;
esac