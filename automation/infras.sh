#!/bin/bash
set -e  # Exit immediately if any command fails

cmd=$1
cmds=('configure' 'create' 'destroy' 'install' 'run' 'pull')

configure() {
    ./scripts/generate-ssh-keys.sh
    ./scripts/configure-aws-cli.sh
    terraform init
}

create() {
    terraform apply
    
    # create sample loads based on hosts.yml created by terraform
    python cpex/prototype/scripts/setup.py --loads
}

destroy() {
    terraform destroy
}

install() {
    ansible-playbook -i hosts.yml playbooks/install.yml
}

pull_changes() {
    ansible-playbook -i hosts.yml playbooks/install.yml --tags "checkout_branch"
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
    
    ansible-playbook -i hosts.yml playbooks/main.yml --tags "$tags"
}

case "$cmd" in
    configure)
        configure
        ;;
    create)
        create
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
        echo "Usage: $0 {${cmds[*]}}"
        exit 1
        ;;
esac
