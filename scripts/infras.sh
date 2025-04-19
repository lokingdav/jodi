#!/bin/bash

set -e

MAIN_HOSTS_FILE=hosts/main.yml
TESTNET_HOSTS_FILE=hosts/testnet.yml
LIVENET_HOSTS_FILE=hosts/livenet.yml

run_in_docker() {
    local command=$1
    local app_dir=$(pwd)

    docker run -it --rm \
        -v "$app_dir:/app" \
        -v "$app_dir/docker/data/.aws:/root/.aws" \
        -v "$app_dir/docker/data/.ssh:/root/.ssh" \
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
            run_in_docker "cd deployments && terraform apply && cp $LIVENET_HOSTS_FILE $MAIN_HOSTS_FILE"
            ;;
        testnet)
            echo "Creating Testnet Infrastructure..."
            docker compose --profile testnet up -d
            run_in_docker "cd deployments && cp $TESTNET_HOSTS_FILE $MAIN_HOSTS_FILE"
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
    docker compose --profile testnet down
    rm_files="rm -rf $MAIN_HOSTS_FILE"
    run_in_docker "cd deployments && terraform destroy && $rm_files"
}

install() {
    run_in_docker "cd deployments && ansible-playbook -i $MAIN_HOSTS_FILE playbooks/install.yml"
}

pull_changes() {
    ansible-playbook -i $MAIN_HOSTS_FILE playbooks/install.yml --tags "checkout_branch"
}

runapp() {
    local app=$1
    local pull=$2

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
    
    ansible-playbook -i $MAIN_HOSTS_FILE playbooks/main.yml --tags "$tags"
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
        # Ensure an app name is provided
        if [ -z "$2" ]; then
            echo "Usage: $0 run {cpex|atis}"
            exit 1
        fi
        runapp "$2" "$3"
        ;;
    *)
        echo "Usage: infras {init|create|destroy|install|pull|run} [args...]"
        exit 1
        ;;
esac