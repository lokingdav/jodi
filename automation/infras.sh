#!/bin/bash

cmd=$1
cmds=('configure' 'create' 'destroy')

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
    # rm -rf hosts.yml
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
    *)
        echo "Usage: $0 {${cmds[*]}}"
        exit 1
        ;;
esac