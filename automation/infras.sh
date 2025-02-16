#!/bin/bash
set -e  # Exit immediately if any command fails

cmd=$1
cmds=('configure' 'create' 'destroy' 'install' 'run')

configure() {
    ./scripts/generate-ssh-keys.sh
    ./scripts/configure-aws-cli.sh
    terraform init
}

create() {
    terraform apply
    echo "Pinging all instances..."
}

destroy() {
    terraform destroy
}

install() {
    ansible-playbook -i hosts.yml playbooks/install.yml
}

runapp() {
    local app=$1
    case "$app" in
        cpex)
            tags="stop_cpex,start_cpex"
            ;;
        atis)
            tags="stop_atis,start_atis"
            ;;
        *)
            echo "Unknown app: $app"
            exit 1
            ;;
    esac
    
    ansible-playbook -i hosts.yml playbooks/run.yml --tags "$tags"
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
    run)
        # Ensure an app name is provided
        if [ -z "$2" ]; then
            echo "Usage: $0 run {cpex|atis}"
            exit 1
        fi
        runapp "$2"
        ;;
    *)
        echo "Usage: $0 {${cmds[*]}}"
        exit 1
        ;;
esac
