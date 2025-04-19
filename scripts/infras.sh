#!/bin/bash

set -e

MAIN_HOSTS_FILE=hosts.yml
TESTNET_COMPOSE_FILE=compose.testnet.yml

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
        cpex-experiment \
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
            run_in_docker "python cpex/prototype/scripts/setup.py --testnet"
            ;;
        *)
            echo "Available subcommands for create:"
            echo "create {livenet|testnet}"
            exit 1
            ;;
    esac

    run_in_docker "python cpex/prototype/scripts/setup.py --loads"
    
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

    if [ -z "$app" ]; then
        echo "Usage: run {cpex|atis}"
        exit 1
    fi

    tags="stop_services,clear_logs"
    if [ "$pull" == "--pull" ]; then
        tags="$tags,checkout_branch"
    fi

    case "$app" in
        cpex)
            tags="$tags,start_cpex"
            ;;
        atis)
            tags="$tags,start_atis"
            ;;
        *)
            echo "Unknown app: $app"
            exit 1
            ;;
    esac
    
    run_in_docker "cd deployments && ansible-playbook -i $MAIN_HOSTS_FILE playbooks/main.yml --tags $tags"
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
    install)
        install
        ;;
    pull)
        pull_changes
        ;;
    run)
        runapp "$2" "$3"
        ;;
    *)
        echo "Usage: infras {init|create|destroy|install|pull|run} [args...]"
        exit 1
        ;;
esac